from flask import make_response
from flask_restx import Namespace, Resource, reqparse
from sqlalchemy.exc import NoResultFound

from te_canvas.translator import TemplateError, Translator

ns = Namespace("config", description="Config API", prefix="/api")


class Config(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    key_parser = reqparse.RequestParser()
    key_parser.add_argument("key", type=str, required=True)

    key_value_parser = reqparse.RequestParser()
    key_value_parser.add_argument("key", type=str, required=True)
    key_value_parser.add_argument("value", type=str, required=True)

    @ns.param("key", "Key")
    @ns.param("value", "Value")
    def put(self):
        args = self.key_value_parser.parse_args(strict=True)
        self.db.set_config(args.key, args.value)

    @ns.param("key", "Key")
    @ns.produces(["text/plain"])
    def get(self):
        args = self.key_parser.parse_args(strict=True)
        try:
            resp = make_response(self.db.get_config(args.key))
            resp.mimetype = "text/plain"
            return resp
        except NoResultFound:
            return "", 404

    @ns.param("key", "Key")
    def delete(self):
        args = self.key_parser.parse_args(strict=True)
        self.db.delete_config(args.key)


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
