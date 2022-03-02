from flask_restx import Namespace, Resource, reqparse
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError, NoResultFound

from te_canvas.db import DeleteFlagAlreadySet

connection_api = Namespace(
    "connection",
    description="API for handling connections between TimeEdit and Canvas",
    prefix="/api",
)


class ConnectionApi(Resource):

    # TODO: Is this correct subclassing? We need to know the supertype constructor's signature?
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    # --- POST ----
    #
    # If a Connection exists for canvas_group and te_group this is a NO-OP.
    #

    # NOTE: Will be deprecated in flask-restx 2.0
    post_parser = reqparse.RequestParser()
    post_parser.add_argument("canvas_group", type=str, required=True)
    post_parser.add_argument("te_group", type=str, required=True)

    @connection_api.param("canvas_group", "Canvas group ID")
    @connection_api.param("te_group", "TimeEdit group ID")
    @connection_api.response(204, "Connection created")
    @connection_api.response(404, "Connection already exists")
    @connection_api.response(
        409,
        "Connection is flagged for deletion, but has not been deleted yet.",
    )
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        try:
            self.db.add_connection(args.canvas_group, args.te_group)
            return "", 204
        except UniqueViolation:
            return {
                "message": f"Connection already exists.",
            }, 404
        except DeleteFlagAlreadySet:
            return {
                "message": "Connection is flagged for deletion, but has not been deleted yet. Try again later.",
            }, 409

    # --- DELETE ----
    #

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("canvas_group", type=str, required=True)
    delete_parser.add_argument("te_group", type=str, required=True)

    @connection_api.param("canvas_group", "Canvas group ID")
    @connection_api.param("te_group", "TimeEdit group ID")
    @connection_api.response(204, "Connection deleted")
    @connection_api.response(404, "Connection not found")
    @connection_api.response(
        409,
        "Connection is flagged for deletion, but has not been deleted yet.",
    )
    def delete(self):
        args = self.delete_parser.parse_args(strict=True)
        try:
            self.db.delete_connection(args.canvas_group, args.te_group)
            return "", 204
        except NoResultFound:
            return {"message": "Connection not found."}, 404
        except DeleteFlagAlreadySet:
            return {
                "message": "Connection is flagged for deletion, but has not been deleted yet. Try again later.",
            }, 409
        # We raise the rest of exceptions. This includes faulty states like
        # where multiple connections are found with the same ID pair, in which
        # case one() raises MultipleResultsFound. On the API side this would
        # result in a 500 internal server error.

    # --- GET ----
    #

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("canvas_group", type=str)

    @connection_api.param("canvas_group", "Canvas group ID")
    def get(self):
        args = self.get_parser.parse_args(strict=True)
        return [
            {"canvas_group": x, "te_group": y, "delete_flag": z}
            for (x, y, z) in self.db.get_connections(args.canvas_group)
        ]
