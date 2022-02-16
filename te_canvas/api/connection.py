from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

import te_canvas.log as log
from te_canvas.db import DB

logger = log.get_logger()
db = DB()

connection_api = Namespace(
    "connection",
    description="API for handling connections between TimeEdit and Canvas",
    prefix="/api",
)

# (?): Not RESTful to use a single endpoint with IDs in query string?


class ConnectionApi(Resource):

    # NOTE: Will be deprecated in flask-restx 2.0

    # --- POST ----
    #
    # If a Connection exists for canvas_group and te_group this is a NO-OP.
    #

    post_parser = reqparse.RequestParser()
    post_parser.add_argument("canvas_group", type=str, required=True)
    post_parser.add_argument("te_group", type=str, required=True)

    @connection_api.param("canvas_group", "Canvas group ID")
    @connection_api.param("te_group", "TimeEdit group ID")
    @connection_api.response(409, 'Connection already exists')
    @connection_api.response(204, 'Connection created')
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        try:
            db.add_connection(args.canvas_group, args.te_group)
        except IntegrityError as e:
            # This conditional required to go from sqlalchemy's wrapper
            # IntegrityError to psycopg2-specific UniqueViolation.
            if isinstance(e.orig, UniqueViolation):
                return {
                    "message": f"Connection ({args.canvas_group}, {args.te_group}) already exists.",
                }, 409
            raise
        return "", 204

    # --- DELETE ----
    #

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("canvas_group", type=str, required=True)
    delete_parser.add_argument("te_group", type=str, required=True)

    @connection_api.param("canvas_group", "Canvas group ID")
    @connection_api.param("te_group", "TimeEdit group ID")
    @connection_api.response(400, 'Connection not found')
    @connection_api.response(204, 'Connection deleted')
    def delete(self):
        args = self.delete_parser.parse_args(strict=True)
        try:
            db.delete_connection(args.canvas_group, args.te_group)
        except NoResultFound:
            return {"message": "Connection not found."}, 400
        # We raise the rest of exceptions. This includes the case where multiple
        # connections were found with the same ID pair, in which case one()
        # raises MultipleResultsFound.

        return "", 204

    # --- GET ----
    #

    def get(self):
        return [
            {"canvas_group": x, "te_group": y, "delete_flag": z}
            for (x, y, z) in db.get_connections()
        ]


connection_api.add_resource(ConnectionApi, "")
