from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import SQLAlchemyError, NoResultFound, IntegrityError
from psycopg2.errors import UniqueViolation

import te_canvas.db.model as db
import te_canvas.log as log

logger = log.get_logger()

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
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        try:
            db.add_connection(args.canvas_group, args.te_group)
        except IntegrityError as e:
            if not isinstance(e.orig, UniqueViolation):
                logger.error(e)
                return {"status": "failure"}, 500

            return {
                "status": "unchanged",
                "message": f"Connection ({args.canvas_group}, {args.te_group}) already exists.",
            }
        except SQLAlchemyError as e:
            logger.error(e)
            return {"status": "failure"}, 500
        return {"status": "success"}

    # --- DELETE ----
    #

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("canvas_group", type=str, required=True)
    delete_parser.add_argument("te_group", type=str, required=True)

    @connection_api.param("canvas_group", "Canvas group ID")
    @connection_api.param("te_group", "TimeEdit group ID")
    def delete(self):
        args = self.delete_parser.parse_args(strict=True)
        try:
            db.delete_connection(args.canvas_group, args.te_group)
        except NoResultFound:
            return {"status": "unchanged", "message": "Connection not found."}
        except SQLAlchemyError as e:
            # Includes if multiple connections were found with the same ID pair,
            # in which case one() raises MultipleResultsFound.
            logger.error(e)
            return {"status": "failure"}, 500
        return {"status": "success"}

    # --- GET ----
    #

    def get(self):
        try:
            data = {
                "status": "success",
                "data": [
                    {"canvas_group": x, "te_group": y, "delete_flag": z}
                    for (x, y, z) in db.get_connections()
                ],
            }
        except SQLAlchemyError as e:
            logger.error(e)
            data = {"status": "failure"}, 500

        return data


connection_api.add_resource(ConnectionApi, "")
