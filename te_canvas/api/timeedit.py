from flask_restx import Namespace, Resource, reqparse

import te_canvas.log as log
from te_canvas.timeedit import TimeEdit

logger = log.get_logger()

timeedit_api = Namespace(
    "timeedit",
    description="API for getting data from TimeEdit",
    prefix="/api",
)

timeedit = TimeEdit()


class Objects(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument("type", type=str, required=True)
    parser.add_argument("number_of_objects", type=int)
    parser.add_argument("begin_index", type=int)
    parser.add_argument("search_string", type=str)

    @timeedit_api.param("type", "Type of object to get.")
    @timeedit_api.param("number_of_objects", "Number of objects to return, max 1000.")
    @timeedit_api.param("begin_index", "Starting index of requested object sequence.")
    @timeedit_api.param("search_string", "general.id or general.title must contain this string")
    def get(self):
        args = self.parser.parse_args(strict=True)
        type = args["type"]
        n = args["number_of_objects"]
        i = args["begin_index"]
        s = args["search_string"]
        if n or i:
            data = timeedit.find_objects(type, n or 1000, i or 0, s)
        else:
            data = timeedit.find_objects_all(type, s)
        return data


class Object(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument("extid", type=str, required=True)

    @timeedit_api.param("extid", "External id.")
    def get(self):
        args = self.parser.parse_args(strict=True)
        extid = args["extid"]
        res = timeedit.get_object(extid)
        if res is None:
            return {"message": f"Object {extid} not found"}, 404
        return res


class Types(Resource):
    def get(self):
        return timeedit.find_types_all()


timeedit_api.add_resource(Objects, "/objects")
timeedit_api.add_resource(Object, "/object")
timeedit_api.add_resource(Types, "/types")
