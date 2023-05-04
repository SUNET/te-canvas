from flask import make_response
from flask_restx import Namespace, Resource, reqparse
from sqlalchemy.exc import NoResultFound  # type: ignore

from te_canvas.translator import TemplateError, Translator

ns = Namespace("config", description="Config API", prefix="/api")


class Template(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    def get(self):
        try:
            templates = {"title": [], "location": [], "description": []}
            for [i, n, t, f] in self.db.get_template_config():
                templates[n].append({"id": i, "te_type": t, "te_fields": f})
            return templates
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
