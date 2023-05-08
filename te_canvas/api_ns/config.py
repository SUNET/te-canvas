from flask import make_response
from flask_restx import Namespace, Resource, reqparse
from sqlalchemy.exc import NoResultFound  # type: ignore
from psycopg2.errors import UniqueViolation

from te_canvas.translator import TemplateError, Translator

ns = Namespace("config", description="Config API", prefix="/api")


class Template(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    def get(self):
        try:
            return self.db.get_template_config()
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

    @ns.param("name", "title | location | description")
    @ns.param("te_type", "Timeedit object type")
    @ns.param("te_field", "Object type field")
    @ns.response(204, "Config template added")
    @ns.response(400, "Missing parameters")
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        try:
            self.db.add_template_config(args.name, args.te_type, args.te_field)
            return "", 204
        except UniqueViolation:
            return {"message": "Type and field combination already exist"}, 400


class Ok(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]
        self.timeedit = kwargs["timeedit"]

    @ns.produces(["text/plain"])
    def get(self):
        status = True
        try:
            Translator(self.db, self.timeedit)
        except TemplateError:
            status = False
        resp = make_response(str(status))
        resp.mimetype = "text/plain"
        return resp
