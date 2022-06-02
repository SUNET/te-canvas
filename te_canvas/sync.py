import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BlockingScheduler
from pytz import utc

from te_canvas.canvas import Canvas
from te_canvas.db import DB, Connection, Event, flat_list
from te_canvas.log import get_logger
from te_canvas.timeedit import TimeEdit
from te_canvas.translator import TAG_TITLE, TemplateError, Translator
from te_canvas.util import State



class JobScheduler(object):
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
        self.logger.info(f"Adding job to scheduler: interval={seconds}")
        return self.scheduler.add_job(func, "interval", seconds=seconds, kwargs=kwargs, next_run_time=datetime.now(utc))


class Syncer:
    def __init__(self, db: DB = None, timeedit: TimeEdit = None, canvas: Canvas = None):
        self.logger = get_logger()

        try:
            self.max_workers = int(os.environ["MAX_WORKERS"])
        except Exception as e:
            self.logger.critical(f"Missing env var: {e}")
            sys.exit(-1)

        self.db = db or DB()
        self.canvas = canvas or Canvas()
        self.timeedit = timeedit or TimeEdit()

        # Mapping canvas_group to in-memory State:s
        self.states: dict[str, State] = {}

        # Set to false at start of each sync, set to true at completion
        self.sync_complete: dict[str, bool] = {}

    # Modifications to detect:
    # 1. Connection modified
    #     1a. Connection added
    #     1b. Connection flagged for deletion
    # 2. TE event modified
    # 3. TE event created
    # 4. TE event deleted
    # 5. Tagged Canvas event modified
    # 6. Tagged Canvas event created
    # 7. Tagged Canvas event deleted
    # 8. Template config is edited
    #
    # TODO:
    # 8. sync_job not completed, should be retried
    #
    # Means of detection:
    # 1:   Hash of TE connections not flagged for deletion
    # 2:   Latest modification timestamp in set of TE events
    # 3,4: Hash of TE event IDs
    # 5:   Latest modification timestamp in set of tagged Canvas events
    # 6,7: Hash of tagged Canvas event IDs

    def __state_te(self, canvas_group: str) -> State:
        with self.db.sqla_session() as session:
            # 1
            te_groups = flat_list(
                session.query(Connection.te_group)
                .filter(Connection.canvas_group == canvas_group, Connection.delete_flag == False)
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

    def __state_canvas(self, canvas_group: str) -> State:
        canvas_events = self.canvas.get_events_all(int(canvas_group))

        # 6,7
        canvas_event_ids = [str(e.id) for e in canvas_events if e.title.endswith(TAG_TITLE)]

        # 5
        canvas_event_modify_date = (
            ""
            if len(canvas_events) == 0
            else str(max([e.updated_at for e in canvas_events if e.title.endswith(TAG_TITLE)]))
        )

        sep = ":"
        return {
            "canvas_event_ids": sep.join(canvas_event_ids),
            "canvas_event_modify_date": canvas_event_modify_date,
        }

    def __has_changed(self, prev_state: Optional[State], state: State) -> bool:
        return state != prev_state

    # Sync events for all Canvas groups. For rate limiting concerns, the maximum number of
    # concurrent calls to Canvas or TimeEdit is equal to max_workers.
    def sync_all(self):
        self.logger.info("Sync job started")

        with self.db.sqla_session() as session:  # Any exception -> session.rollback()
            groups = flat_list(session.query(Connection.canvas_group).distinct().order_by(Connection.canvas_group))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            res = list(executor.map(self.sync_one, groups))

        self.logger.info(
            f"Sync job completed; {len([x for x in res if x])} Canvas groups synced; {len([x for x in res if not x])} skipped"
        )

    # Sync events for one Canvas group. Returns False if the group was skipped due to change
    # detection OR template error, otherwise True.
    #
    # Invariant 1: Events in database is a superset of (our) events on Canvas.
    # Invariant 2: For every event E in the database, there exists a connection C s.t.
    #              C.canvas_group = E.canvas_group and C.te_group = E.te_group.
    def sync_one(self, canvas_group: str) -> bool:
        with self.db.sqla_session() as session:  # Any exception -> session.rollback()
            self.logger.info(f"{canvas_group}: Processing")

            # When a Translator is instantiated it reads template config from the DB and is after
            # this static. So we initiate a new one for each sync, and diff for change detection
            # with the previous instance.
            try:
                translator = Translator(self.db, self.timeedit)
            except TemplateError:
                self.logger.warning(f"{canvas_group}: Template error, skipping")
                return False

            # Change detection
            prev_state = self.states.get(canvas_group)
            new_state = self.__state_te(canvas_group) | self.__state_canvas(canvas_group) | translator.state()
            self.states[canvas_group] = new_state  # TODO: Verify thread safe
            self.logger.debug(f"State: {new_state}")

            if not self.__has_changed(prev_state, new_state) and self.sync_complete.get(canvas_group, False):
                self.logger.info(f"{canvas_group}: Nothing changed, skipping")
                return False

            self.sync_complete[canvas_group] = False

            # Remove all events previously added by us to this Canvas group
            # TODO: Should this just use clear_events_tagged instead? Can we avoid storing events locally at all?
            self.logger.info(
                f"{canvas_group}: Deleting events ({session.query(Event).filter(Event.canvas_group == canvas_group).count()} events)"
            )
            for event in (
                session.query(Event).filter(Event.canvas_group == canvas_group).order_by(Event.canvas_id, Event.te_id)
            ):
                # If this event does not exist on Canvas, this is a NOOP and no
                # exception is raised.
                self.canvas.delete_event(event.canvas_id)

            # Clear deleted events
            session.query(Event).filter(Event.canvas_group == canvas_group).delete()

            # Delete flagged connections
            session.query(Connection).filter(
                Connection.canvas_group == canvas_group,
                Connection.delete_flag == True,
            ).delete()

            # Push to Canvas and add to database
            te_groups = flat_list(
                session.query(Connection.te_group)
                .filter(Connection.canvas_group == canvas_group)
                .order_by(Connection.canvas_group, Connection.te_group)
            )

            reservations = self.timeedit.find_reservations_all(te_groups, translator.return_types)

            self.logger.info(f"{canvas_group}: Adding events: {te_groups} ({len(reservations)} events)")
            for r in reservations:
                # Try/finally ensures invariant 1.
                try:
                    canvas_event = self.canvas.create_event(
                        translator.canvas_event(r) | {"context_code": f"course_{canvas_group}"}
                    )
                finally:
                    session.add(
                        Event(
                            te_id=r["id"],
                            canvas_id=canvas_event.id,
                            canvas_group=canvas_group,
                        )
                    )

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

            return True


if __name__ == "__main__":
    syncer = Syncer()

    jobs = JobScheduler()
    jobs.add(syncer.sync_all, 10, {})
    jobs.start()
