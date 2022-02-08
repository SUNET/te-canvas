from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import DBAPIError

from te_canvas.te import get_objects, get_objects_all, get_types_all
import te_canvas.log as log

logger = log.get_logger()

timeedit_api = Namespace(
    "timeedit",
    description="API for getting data from TimeEdit",
    prefix="/api",
)


class Objects(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument("type", type=str, required=True)
    parser.add_argument("number_of_objects", type=int)
    parser.add_argument("begin_index", type=int)
    parser.add_argument("search_string", type=str)

    @timeedit_api.param("type", "Type of object to get.")
    @timeedit_api.param("number_of_objects", "Number of objects to return, max 1000.")
    @timeedit_api.param("begin_index", "Starting index of requested object sequence.")
    @timeedit_api.param("search_string", "general.id must contain this string")
    def get(self):
        args = self.parser.parse_args(strict=True)
        type = args["type"]
        n = args["number_of_objects"]
        i = args["begin_index"]
        s = args["search_string"]
        if n or i:
            data = get_objects(type, n or 1000, i or 0, s)
        else:
            data = get_objects_all(type, s)

        # TODO: Error handling
        return {"status": "success", "data": data}


class Types(Resource):
    def get(self):
        return {"status": "success", "data": get_types_all()}


timeedit_api.add_resource(Objects, "/objects")
timeedit_api.add_resource(Types, "/types")
