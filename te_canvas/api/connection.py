from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import SQLAlchemyError, NoResultFound

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
    id_parser = reqparse.RequestParser()
    id_parser.add_argument("te_group", type=str, required=True)
    id_parser.add_argument("canvas_group", type=str, required=True)

    @connection_api.param("te_group", "TimeEdit group ID")
    @connection_api.param("canvas_group", "Canvas group ID")
    def post(self):
        args = self.id_parser.parse_args(strict=True)
        try:
            db.add_connection(args.te_group, args.canvas_group)
        except SQLAlchemyError as e:
            logger.error(e)
            return {"status": "failure"}, 500
        return {"status": "success"}

    @connection_api.param("te_group", "TimeEdit group ID")
    @connection_api.param("canvas_group", "Canvas group ID")
    def delete(self):
        args = self.id_parser.parse_args(strict=True)
        try:
            db.delete_connection(args.te_group, args.canvas_group)
        except NoResultFound:
            return {"status": "unchanged", "message": "Connection not found."}
            # (?): Also return a different status code than 200?
        except SQLAlchemyError as e:
            # Includes if multiple connections were found with the same ID pair,
            # in which case one() raises MultipleResultsFound.
            logger.error(e)
            return {"status": "failure"}, 500
        return {"status": "success"}

    def get(self):
        try:
            data = {
                "status": "success",
                "data": [
                    {"te_group": x, "canvas_group": y, "delete_flag": z}
                    for (x, y, z) in db.get_connections()
                ],
            }
        except SQLAlchemyError as e:
            logger.error(e)
            data = {"status": "failure"}, 500

        return data


connection_api.add_resource(ConnectionApi, "")
