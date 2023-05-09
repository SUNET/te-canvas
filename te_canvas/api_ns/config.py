from flask import make_response
from flask_restx import Namespace, Resource, reqparse
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import NoResultFound  # type: ignore

ns = Namespace("config", description="Config API", prefix="/api")


class Ok(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("canvas_group", type=str, required=True)

    @ns.param("canvas_group", "Canvas group")
    def get(self):
        args = self.get_parser.parse_args(strict=True)
        res = self.db.get_template_config()
        default = set(n for [_, n, _, _, c] in res if c == "default")
        group = set(n for [_, n, _, _, c] in res if c == args.canvas_group)
        return {"group": [n for n in group], "default": [n for n in default]}


class Template(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    def get(self):
        try:
            template_config = {"title": [], "location": [], "description": []}
            for [i, n, t, f, c] in self.db.get_template_config():
                template_config[n].append({"id": i, "te_type": t, "te_field": f, "canvas_group": c})
            return template_config
        except NoResultFound:
            return "", 404

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("id", type=str, required=True)

    @ns.param("id", "Config template id")
    @ns.response(204, "Config template deleted")
    @ns.response(404, "Config template not found")
    def delete(self):
        args = self.delete_parser.parse_args(strict=True)
        try:
            self.db.delete_template_config(args.id)
            return "", 204
        except NoResultFound:
            return {"message": "Connection not found."}, 404

    post_parser = reqparse.RequestParser()
    post_parser.add_argument("name", type=str, required=True)
    post_parser.add_argument("te_type", type=str, required=True)
    post_parser.add_argument("te_field", type=str, required=True)
    post_parser.add_argument("canvas_group", type=str, required=False)

    @ns.param("name", "title | location | description |")
    @ns.param("te_type", "Timeedit object type")
    @ns.param("te_field", "Object type field")
    @ns.param("canvas_group", "Canvas group")
    @ns.response(204, "Config template added")
    @ns.response(400, "Missing parameters")
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        try:
            self.db.add_template_config(args.name, args.te_type, args.te_field, args.canvas_group)
            return "", 204
        except UniqueViolation:
            return {"message": "Type and field combination already exist"}, 400
