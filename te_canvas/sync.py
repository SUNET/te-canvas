import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BlockingScheduler
from canvasapi.exceptions import CanvasException
from pytz import utc

from te_canvas.canvas import Canvas
from te_canvas.db import DB, Connection, flat_list
from te_canvas.log import get_logger
from te_canvas.timeedit import TimeEdit
from te_canvas.translator import TemplateError, Translator
from te_canvas.types.sync_state import SyncState


class Syncer:
    """
    Syncs TimeEdit events to Canvas.

    Much of the logic has to do with change detection, which is performed before syncing each Canvas
    group. If nothing of relevance has changed since the previous sync of this group, we don't sync.
    This saves us time and avoids unneccesarily breaking URLs to Canvas events. If there is a change
    detected, all events added by te-canvas are deleted and re-added. A sync is thus either full or
    not at all, we don't sync on individual event level.

    Data used for change detection is in-memory only, so on restart te-canvas will perform a full
    resync of all Canvas groups.

    The syncer is mildly parallel with each thread handling the syncing of one Canvas group. Each
    such sync consist of a number of API calls which are performed sequentially within the group.
    Consequently, the number of threads is a maximum on the number of concurrent API calls.

    The number of threads is determined by env var MAX_WORKERS. Set this to 1 to disable
    parallelization.

    Observing the header "X-Rate-Limit-Remaining" with concurrent Canvas API calls to create
    calendar events has determined that the limit seems to lie around 60. Rate limiting on TimeEdit
    should not be a concern.

    We distinguish te-canvas events from other manually added events in Canvas by the string
    TAG_TITLE which is added as a suffix to each te-canvas event.

    Modifications to detect:

    1. Connection modified
        1a. Connection added
        1b. Connection flagged for deletion
    2. TE event modified
    3. TE event created
    4. TE event deleted
    5. Tagged Canvas event modified
    6. Tagged Canvas event created
    7. Tagged Canvas event deleted
    8. Template config edited

    Means of detection:

    1:   Hash of TE connections not flagged for deletion
    2:   Latest modification timestamp in set of TE events
    3,4: Hash of TE event IDs
    5:   Latest modification timestamp in set of tagged Canvas events
    6,7: Hash of tagged Canvas event IDs
    """

    def __init__(self, db: DB = None, timeedit: TimeEdit = None, canvas: Canvas = None):
        self.logger = get_logger()

        try:
            self.max_workers = int(os.environ["MAX_WORKERS"])
        except Exception as e:
            self.logger.critical("Missing env var: %s", e)
            sys.exit(1)

        self.db: DB = db or DB()
        self.canvas = canvas or Canvas()
        self.timeedit = timeedit or TimeEdit()

        # Mapping canvas_group to in-memory State:s
        self.states: dict[str, SyncState] = {}

        # Set to false at start of each sync, set to true at completion
        self.sync_complete: dict[str, bool] = {}

    def __state_te(self, canvas_group: str) -> SyncState:
        """
        Get the TimeEdit state relevant for canvas_group. Number comments reference "modifications
        to detect", see class docstring.
        """
        with self.db.sqla_session() as session:
            # 1
            te_groups = flat_list(
                session.query(Connection.te_group)
                .filter(
                    Connection.canvas_group == canvas_group,
                    Connection.delete_flag == False,
                )
                .order_by(Connection.canvas_group, Connection.te_group)
            )

            te_events = self.timeedit.find_reservations_all(te_groups, {})

            # 3,4
            te_event_ids = [str(e["id"]) for e in te_events]

            # 2
            te_event_modify_date = "" if len(te_events) == 0 else str(max([e["modified"] for e in te_events]))

            sep = ":"
            return {
                "te_groups": sep.join(te_groups),
                "te_event_ids": sep.join(te_event_ids),
                "te_event_modify_date": te_event_modify_date,
            }

    def __state_canvas(self, canvas_group: str) -> SyncState:
        """
        Get the Canvas state relevant for canvas_group. Number comments reference "modifications to
        detect", see class docstring.
        """
        canvas_events = self.canvas.get_events(int(canvas_group))

        # 6,7
        canvas_event_ids = [str(e.id) for e in canvas_events]

        # 5
        canvas_event_modify_date = "" if len(canvas_events) == 0 else str(max([e.updated_at for e in canvas_events]))

        sep = ":"
        return {
            "canvas_event_ids": sep.join(canvas_event_ids),
            "canvas_event_modify_date": canvas_event_modify_date,
        }

    def __has_changed(self, prev_state: Optional[SyncState], state: SyncState) -> bool:
        return state != prev_state

    def sync_all(self):
        """
        Sync events for all configured Canvas groups.

        This function gets all the Canvas groups to sync, and runs through them using a thread pool
        of size MAX_WORKERS.
        """
        self.logger.info("Sync job started")
        self.logger.info("1. [=== In sync_all() ===]")
        self.logger.info(f"db={self.db}")

        with self.db.sqla_session() as session:  # Any exception -> session.rollback()
            groups = flat_list(session.query(Connection.canvas_group).distinct().order_by(Connection.canvas_group))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            res = list(executor.map(self.sync_one, groups))

        self.logger.info(
            "Sync job completed: %s Canvas groups synced:  %s skipped",
            len([x for x in res if x]),
            len([x for x in res if not x]),
        )

    def sync_one(self, canvas_group: str) -> bool:
        """
        Sync events for one Canvas group.

        Returns:
            False if the group was skipped due to change detection or template error, otherwise True.
        """
        self.logger.info(f"** inside sync_one() [canvas_group:{canvas_group}]**")
        with self.db.sqla_session() as session:  # Any exception -> session.rollback()
            self.logger.info("%s: Processing", canvas_group)

            # When a Translator is instantiated it reads template config from the DB and is after
            # this static. So we initiate a new one for each sync, and diff for change detection
            # with the previous instance.
            try:
                translator = Translator(self.db, self.timeedit)
            except TemplateError:
                self.logger.warning("%s: Template error, skipping", canvas_group)
                self.db.update_sync_status(canvas_group, "error")
                return False

            # Change detection
            prev_state = self.states.get(canvas_group)
            try:
                new_state = (
                    self.__state_te(canvas_group)
                    | self.__state_canvas(canvas_group)
                    | translator.get_state(canvas_group)
                )
                self.states[canvas_group] = new_state
                self.logger.debug("State: %s", new_state)
                self.logger.info("************** [Sync.one.prev_state] ***************")
                self.logger.info(prev_state)
                self.logger.info("************** [Sync.one.new_state] ***************")
                self.logger.info(new_state)
                self.logger.info("*-----------------------------------------------------")
                if not self.__has_changed(prev_state, new_state) and self.sync_complete.get(canvas_group, False):
                    self.logger.info("%s: Nothing changed, skipping", canvas_group)
                    self.db.update_sync_status(canvas_group, "success")
                    return False
            except CanvasException as e:
                self.logger.error("Canvas API error while getting state: %s", e.message)
                self.db.update_sync_status(canvas_group, "error")
                return False
            except Exception as e:
                self.logger.info(f"ERROR=>{e}")
                self.logger.error(traceback.format_exc())
                self.logger.error("Error while getting state", stack_info=True)
                self.db.update_sync_status(canvas_group, "error")
                return False

            self.sync_complete[canvas_group] = False

            # Update sync status.
            self.logger.info("Updating sync state to in_progress for %s", canvas_group)
            self.db.update_sync_status(canvas_group, "in_progress")

            # Remove all events previously added by us to this Canvas group
            self.logger.info("%s: Deleting events", canvas_group)
            try:
                deleted = self.canvas.delete_events(int(canvas_group))
                self.logger.info("%s: Deleted %s events", canvas_group, len(deleted))
            except CanvasException as e:
                self.logger.error("Canvas API error: %s", e.message)
                self.db.update_sync_status(canvas_group, "error")
                return False
            except Exception as e:
                self.logger.error("Non-defined Canvas API error")
                self.db.update_sync_status(canvas_group, "error")
                return False

            # Delete flagged connections
            deleted_flagged_count = (
                session.query(Connection)
                .filter(
                    Connection.canvas_group == canvas_group,
                    Connection.delete_flag == "t",
                )
                .delete()
            )
            self.logger.info(
                "%s: Deleted %s flagged connections",
                canvas_group,
                deleted_flagged_count,
            )

            # Get te_groups
            te_groups = flat_list(
                session.query(Connection.te_group)
                .filter(Connection.canvas_group == canvas_group)
                .order_by(Connection.canvas_group, Connection.te_group)
            )

            reservations = self.timeedit.find_reservations_all(te_groups, translator.get_return_types(canvas_group))
            self.logger.info("************** [Sync.one.canvas_group] ***************")
            self.logger.info(canvas_group)
            self.logger.info("************** [Sync.one.te_groups] ***************")
            self.logger.info(te_groups)
            self.logger.info("************** [Sync.one.return_types] ***************")
            self.logger.info(translator.return_types)
            self.logger.info("************** [Sync.one.get_return_types] ***************")
            self.logger.info(translator.get_return_types(canvas_group))
            self.logger.info("*-----------------------------------------------------")
            self.logger.info(
                "%s: Adding events: %s (%s events)",
                canvas_group,
                te_groups,
                len(reservations),
            )

            try:
                self.logger.info("************** [Sync.one.Reservations] ***************")
                self.logger.info(reservations)
                self.logger.info("*-----------------------------------------------------")
                for r in reservations:
                    new_events = translator.canvas_event(r, canvas_group) | {"context_code": f"course_{canvas_group}"}
                    self.canvas.create_event(new_events)
            except CanvasException as e:
                self.logger.error("Canvas API error: %s", e.message)
                self.db.update_sync_status(canvas_group, "error")
                return False
            except Exception as e:
                self.logger.error("Non-defined Canvas API error")
                self.db.update_sync_status(canvas_group, "error")
                return False

            # Record new Canvas state
            #
            # TODO: Race condition here, if something changed on Canvas between being added by
            # us and this state get, it will not be detected. Can be fixed by building state
            # from the calls to Canvas.create_event instead of doing a state get afterwards.
            #
            prev_state = self.states[canvas_group]  # Implicit assert that this is not None
            new_state = prev_state | self.__state_canvas(canvas_group)
            self.states[canvas_group] = new_state

            self.sync_complete[canvas_group] = True

            # Update sync status.
            self.logger.info("Updating sync state to success for %s", canvas_group)
            self.db.update_sync_status(canvas_group, "success")

            return True


class JobScheduler(object):
    """
    Thin wrapper around APScheduler.
    """

    def __init__(self):
        self.scheduler = BlockingScheduler(timezone=utc)
        self.logger = get_logger()

        def listener(event):
            self.logger.warning(f"Job raised an Exception: {event.exception.__class__.__name__}: {event.exception}")

        self.scheduler.add_listener(listener, EVENT_JOB_ERROR)

    def get(self):
        return self.scheduler

    def start(self):
        self.logger.info("Starting scheduler.")
        return self.scheduler.start()

    def stop(self):
        self.logger.info("Stopping scheduler.")
        return self.scheduler.shutdown()

    def add(self, func, seconds, kwargs):
        self.logger.info("Adding job to scheduler: interval=%s", seconds)
        return self.scheduler.add_job(
            func,
            "interval",
            seconds=seconds,
            kwargs=kwargs,
            next_run_time=datetime.now(utc),
        )


if __name__ == "__main__":
    syncer = Syncer()
    jobs = JobScheduler()
    jobs.add(syncer.sync_all, 10, {})
    jobs.start()
