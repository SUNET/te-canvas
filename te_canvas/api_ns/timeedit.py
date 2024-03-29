from flask_restx import Namespace, Resource, reqparse

import te_canvas.log as log
from te_canvas.timeedit import TimeEdit

logger = log.get_logger()

ns = Namespace(
    "timeedit",
    description="API for getting data from TimeEdit",
    prefix="/api",
)


class Objects(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.timeedit = kwargs["timeedit"]

    parser = reqparse.RequestParser()
    parser.add_argument("type", type=str, required=True)
    parser.add_argument("number_of_objects", type=int)
    parser.add_argument("begin_index", type=int)
    parser.add_argument("search_string", type=str)

    @ns.param("type", "Type of object to get.")
    @ns.param("number_of_objects", "Number of objects to return, max 1000.")
    @ns.param("begin_index", "Starting index of requested object sequence.")
    @ns.param("search_string", "general.id or general.title must contain this string")
    def get(self):
        args = self.parser.parse_args(strict=True)
        type = args["type"]
        n = args["number_of_objects"]
        i = args["begin_index"]
        s = args["search_string"]
        if n or i:
            data = self.timeedit.find_objects(type, n or 1000, i or 0, s)
        else:
            data = self.timeedit.find_objects_all(type, s)
        return data


class Object(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.timeedit = kwargs["timeedit"]

    parser = reqparse.RequestParser()
    parser.add_argument("extid", type=str, required=True)

    @ns.param("extid", "External id.")
    def get(self):
        args = self.parser.parse_args(strict=True)
        extid = args["extid"]
        res = self.timeedit.get_object(extid)
        if res is None:
            return {"message": f"Object {extid} not found"}, 404
        return res


class Types(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.timeedit = kwargs["timeedit"]
        self.db = kwargs["db"]

    parser = reqparse.RequestParser()
    parser.add_argument("whitelisted", type=str)

    def get(self):
        args = self.parser.parse_args(strict=True)
        all_types = self.timeedit.find_types_all()
        if args["whitelisted"] != "true":
            return all_types
        whitelist_types = self.db.get_whitelist_types()
        return dict(filter(lambda pair: pair[0] in whitelist_types, all_types.items()))


class Fields(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.timeedit: TimeEdit = kwargs["timeedit"]

    parser = reqparse.RequestParser()
    parser.add_argument("extid", type=str, required=True)

    @ns.param("extid", "External id.")
    def get(self):
        args = self.parser.parse_args(strict=True)
        if args["extid"] == "reservation":
            return [self.timeedit.get_field_defs(field) for field in self.timeedit.find_reservation_fields()]
        fields = self.timeedit.find_object_fields(args["extid"])
        if fields is None:
            return {"message": f"Object {args['extid']} not found"}, 404
        field_defs = [self.timeedit.get_field_defs(field) for field in fields]
        return list(filter(lambda field_def: field_def != {}, field_defs))
