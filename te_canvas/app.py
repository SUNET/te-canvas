import os

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


class App:
    def __init__(self, db):
        self.logger = get_logger()

        self.db = db
        self.canvas = Canvas()
        self.timeedit = TimeEdit()

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
        connection_api.add_resource(
            ConnectionApi, "", resource_class_kwargs={"db": self.db}
        )
        api.add_namespace(connection_api)

        @self.flask.after_request
        def log_request(response):
            self.logger.info(
                "[API] Method: {}, Status: {}, URL: {}, JSON: {}".format(
                    request.method, response.status_code, request.url, request.json
                )
            )
            return response

    def sync_job(self):
        self.logger.info("Sync job started")
        canvas_groups_n = 0
        with self.db.sqla_session() as session:  # Any exception -> session.rollback()
            # Note the comma!
            for (canvas_group,) in session.query(Connection.canvas_group).distinct():
                canvas_groups_n += 1

                # Remove all events previously added by us to this Canvas group
                for event in session.query(Event).filter(
                    Event.canvas_group == canvas_group
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
                    session.query(Connection.te_group).filter(
                        Connection.canvas_group == canvas_group
                    )
                )

                self.logger.info(f"Processing: {te_groups} → {canvas_group}")
                for r in self.timeedit.find_reservations_all(te_groups):
                    # Try/finally ensures invariant 1.
                    try:
                        # TODO: Use configured values to create description.
                        # TODO: Handle missing properties gracefully, i.e. catch KeyError.
                        canvas_event = self.canvas.create_event(
                            {
                                "context_code": f"course_{canvas_group}",
                                "title": r["activity"]["activity.id"],
                                "location_name": r["room"]["room.name"],
                                "description": "<br>".join(
                                    [
                                        r["courseevt"]["courseevt.coursename"],
                                        r["person_staff"]["person.fullname"],
                                    ]
                                ),
                                "start_at": r["start_at"],
                                "end_at": r["end_at"],
                            }
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
            f"Sync job completed; {canvas_groups_n} Canvas groups processed"
        )


app = App(DB())
