import os
from typing import Optional

from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api, Namespace

from te_canvas.api.canvas import canvas_api
from te_canvas.api.connection import ConnectionApi
from te_canvas.api.timeedit import timeedit_api
from te_canvas.api.version import version_api
from te_canvas.canvas import Canvas
from te_canvas.db import DB, Connection, Event, flat_list
from te_canvas.log import get_logger
from te_canvas.timeedit import TimeEdit
from te_canvas.translator import Translator

State = dict[str, str]


class App:
    def __init__(self, db):
        self.logger = get_logger()

        self.db = db
        self.canvas = Canvas()
        self.timeedit = TimeEdit()
        self.translator = Translator(
            os.environ["EVENT_TITLE"],
            os.environ["EVENT_LOCATION"],
            os.environ["EVENT_DESCRIPTION"],
        )

        self.flask = Flask(__name__)
        self.flask.config["SECRET_KEY"] = os.urandom(128)

        CORS(self.flask, resources={r"/api/*": {"origins": "*"}})

        api = Api(self.flask, prefix="/api")
        api.add_namespace(version_api)
        api.add_namespace(timeedit_api)
        api.add_namespace(canvas_api)

        connection_api = Namespace(
            "connection",
            description="API for handling connections between TimeEdit and Canvas",
            prefix="/api",
        )
        connection_api.add_resource(ConnectionApi, "", resource_class_kwargs={"db": self.db})
        api.add_namespace(connection_api)

        @self.flask.after_request
        def log_request(response):
            self.logger.info(
                "[API] Method: {}, Status: {}, URL: {}, JSON: {}".format(
                    request.method, response.status_code, request.url, request.json
                )
            )
            return response

        # Mapping canvas_group to in-memory State:s
        self.states: dict[str, State] = {}

    # Modifications to detect:
    # 1. Connection modified
    #     1a. Connection added
    #     1b. Connection flagged for deletion
    # 2. TE event modified
    # 3. TE event created
    # 4. TE event deleted
    #
    # TODO:
    # 5. sync_job not completed, should be retried
    # 6. Canvas event modified?
    #
    # Means of detection:
    # 1:   Hash of TE connections not flagged for deletion
    # 2:   Latest modification timestamp in set of TE events
    # 3,4: Hash of TE event IDs
    def __state(self, canvas_group: str) -> State:
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
                # Change detection
                prev_state = self.states.get(canvas_group)
                new_state = self.__state(canvas_group)
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

                reservations = self.timeedit.find_reservations_all(te_groups, self.translator.return_types)
                self.logger.info(f"Adding events: {te_groups} → {canvas_group} ({len(reservations)} events)")
                for r in reservations:
                    # Try/finally ensures invariant 1.
                    try:
                        canvas_event = self.canvas.create_event(
                            self.translator.canvas_event(r) | {"context_code": f"course_{canvas_group}"}
                        )
                    finally:
                        session.add(
                            Event(
                                te_id=r["id"],
                                canvas_id=canvas_event.id,
                                canvas_group=canvas_group,
                            )
                        )
        self.logger.info(
            f"Sync job completed; {canvas_groups_synced} Canvas groups synced; {canvas_groups_skipped} skipped"
        )


app = App(DB())


def get_flask():
    return App(DB()).flask


if __name__ == "__main__":
    app.sync_job()
