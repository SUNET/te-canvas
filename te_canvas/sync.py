from typing import Optional

from apscheduler.schedulers.background import BlockingScheduler
from pytz import utc

from te_canvas.canvas import Canvas
from te_canvas.db import DB, Connection, Event, flat_list
from te_canvas.log import get_logger
from te_canvas.timeedit import TimeEdit
from te_canvas.translator import TAG_TITLE, Translator, TemplateError

State = dict[str, str]


class JobScheduler(object):
    def __init__(self):
        self.scheduler = BlockingScheduler(timezone=utc)
        self.logger = get_logger()

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
        return self.scheduler.add_job(func, "interval", seconds=seconds, kwargs=kwargs)


class Syncer:
    def __init__(self, db: DB = None, timeedit: TimeEdit = None, canvas: Canvas = None):
        self.logger = get_logger()

        self.db = db or DB()
        self.canvas = canvas or Canvas()
        self.timeedit = timeedit or TimeEdit()

        # Mapping canvas_group to in-memory State:s
        self.states: dict[str, State] = {}

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

    def __state_translator(self, translator: Translator) -> State:
        res = {}
        for k in ["title", "location", "description"]:
            res[k] = translator.template(k)
        return res

    def __has_changed(self, prev_state: Optional[State], state: State) -> bool:
        return state != prev_state

    # Invariant 1: Events in database is a superset of (our) events on Canvas.
    # Invariant 2: For every event E in the database, there exists a connection C s.t.
    #              C.canvas_group = E.canvas_group and
    #              C.te_group = E.te_group.
    def sync_job(self):
        self.logger.info("Sync job started")
        canvas_groups_synced = 0
        canvas_groups_skipped = 0

        with self.db.sqla_session() as session:  # Any exception -> session.rollback()
            # Note the comma!
            for (canvas_group,) in session.query(Connection.canvas_group).distinct().order_by(Connection.canvas_group):
                self.logger.info(f"Processing {canvas_group}")

                # When a Translator is instantiated it reads template config
                # from the DB and is after this static. So we initiate a new one
                # for each synced canvas group, and diff for change detection
                # with the previous instance.
                #
                # This could be done on the larger sync job level, but to
                # simplify change detection and to prepare for group level
                # parallellization we do this for each synced group.
                try:
                    translator = Translator(self.db, self.timeedit)
                except TemplateError:
                    self.logger.warning(f"Template error, skipping {canvas_group}")
                    # Not break, so we still try again with the next group,
                    # since we decided translator is created on group level for
                    # now.
                    continue

                # Change detection
                prev_state = self.states.get(canvas_group)
                new_state = (
                    self.__state_te(canvas_group)
                    | self.__state_canvas(canvas_group)
                    | self.__state_translator(translator)
                )
                self.states[canvas_group] = new_state
                self.logger.debug(f"State: {new_state}")

                if not self.__has_changed(prev_state, new_state):
                    self.logger.info(f"Skipping {canvas_group}, nothing changed")
                    canvas_groups_skipped += 1
                    continue

                canvas_groups_synced += 1

                # Remove all events previously added by us to this Canvas group
                self.logger.info(
                    f"Deleting events for {canvas_group} ({session.query(Event).filter(Event.canvas_group == canvas_group).count()} events)"
                )
                for event in (
                    session.query(Event)
                    .filter(Event.canvas_group == canvas_group)
                    .order_by(Event.canvas_id, Event.te_id)
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

                self.logger.info(f"Adding events: {te_groups} → {canvas_group} ({len(reservations)} events)")
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
                # TODO: Race condition here, if something changed on Canvas
                # between being added by us and this state get, it will not be
                # detected. Can be fixed by building state from the calls to
                # Canvas.create_event instead of doing a state get afterwards.
                prev_state = self.states[canvas_group]  # Implicit assert that this is not None
                new_state = prev_state | self.__state_canvas(canvas_group)
                self.states[canvas_group] = new_state

        self.logger.info(
            f"Sync job completed; {canvas_groups_synced} Canvas groups synced; {canvas_groups_skipped} skipped"
        )


if __name__ == "__main__":
    syncer = Syncer()
    syncer.sync_job()

    jobs = JobScheduler()
    jobs.add(syncer.sync_job, 10, {})
    jobs.start()
