from flask_restx import Namespace, Resource, reqparse
from psycopg2.errors import NoDataFound, UniqueViolation
import os

from te_canvas.log import get_logger
from te_canvas.db import DB
from te_canvas.timeedit import TimeEdit
from te_canvas.types.config_type import ConfigType  # type: ignore

logger = get_logger()
ns = Namespace("config", description="Config API", prefix="/api")

LTI_ADMIN = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator"

# When set to a truthy value (e.g. "1", "true", "yes", "on") the LTI Administrator
# role check on admin-only endpoints is bypassed. Intended for local development
# where LTI launch headers are not present. NEVER enable this in production.
DEV_BYPASS_ADMIN_AUTH_ENV = "TE_CANVAS_DEV_BYPASS_ADMIN_AUTH"
_TRUTHY = {"1", "true", "yes", "on"}


def _is_admin(lti_roles) -> bool:
    """Return True if the request should be treated as an LTI Administrator.

    Honors the X-LTI-ROLES header; additionally returns True unconditionally if
    the dev bypass env var is set to a truthy value.
    """
    if os.environ.get(DEV_BYPASS_ADMIN_AUTH_ENV, "").strip().lower() in _TRUTHY:
        logger.warning(
            "Admin auth bypass enabled via %s env var; granting admin access without LTI role check.",
            DEV_BYPASS_ADMIN_AUTH_ENV,
        )
        return True
    return LTI_ADMIN in (lti_roles or [])


class Ok(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db: DB = kwargs["db"]

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("canvas_group", type=str, required=True)

    @ns.param("canvas_group", "Canvas group")
    def get(self):
        args = self.get_parser.parse_args(strict=True)
        default = set(ct for [_, ct, _, _, _] in self.db.get_template_config("default"))
        group = set(ct for [_, ct, _, _, _] in self.db.get_template_config(args.canvas_group))
        return {"group": [ct for ct in group], "default": [ct for ct in default]}


class WhitelistTypes(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db: DB = kwargs["db"]

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("X-LTI-ROLES", location="headers")

    def get(self):
        args = self.get_parser.parse_args(strict=True)
        if not _is_admin(args.get("X-LTI-ROLES")):
            return "", 403
        try:
            return self.db.get_whitelist_types()
        except NoDataFound:
            return {"message": "No whitelist type config found"}, 404

    post_parser = reqparse.RequestParser()
    post_parser.add_argument("te_type", type=str, required=True)
    post_parser.add_argument("X-LTI-ROLES", location="headers")

    @ns.param("te_type", "Timeedit object type")
    @ns.response(204, "Whitelist type added")
    @ns.response(400, "Missing parameters")
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        if not _is_admin(args.get("X-LTI-ROLES")):
            return "", 403
        try:
            self.db.add_whitelist_type(args.te_type)
            return "", 204
        except UniqueViolation:
            return {"message": "Type already whitelisted"}, 400

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("te_type", type=str, required=True)
    delete_parser.add_argument("X-LTI-ROLES", location="headers")

    @ns.param("te_type", "Timeedit object type")
    @ns.response(204, "Whitelist type deleted")
    @ns.response(400, "Missing parameters")
    def delete(self):
        args = self.post_parser.parse_args(strict=True)
        if not _is_admin(args.get("X-LTI-ROLES")):
            return "", 403
        try:
            self.db.delete_whitelist_type(args.te_type)
            return "", 204
        except NoDataFound:
            return {"message": "Type already whitelisted"}, 400


class Template(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db: DB = kwargs["db"]
        self.timeedit: TimeEdit = kwargs["timeedit"]

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("canvas_group", type=str, required=True)
    get_parser.add_argument("default", type=str, required=True)
    get_parser.add_argument("X-LTI-ROLES", location="headers")
    
    
    # GET is open to everyone (non-admins see read-only). Mutations remain admin-only.
    @ns.param("default", "Should we get default template?")
    @ns.param("canvas_group", "Canvas group")
    def get(self):
        args = self.get_parser.parse_args(strict=True)
        logger.info("===============  config.Template(Resource) ====================")
        logger.info(f"Template->args: {args}")
        logger.info(f"Template->args.canvas_group: {args.canvas_group}")

        canvas_group = "default" if args.default == "true" else args.canvas_group
        try:
            template_config = {
                ConfigType.TITLE.value: [],
                ConfigType.LOCATION.value: [],
                ConfigType.DESCRIPTION.value: [],
            }
            for [i, ct, t, f, cg] in self.db.get_template_config(canvas_group):
                template_config[ct].append(
                    {
                        "id": i,
                        "te_type": t,
                        "te_field": f,
                        "te_type_name": self.timeedit.get_type(t)["name"],
                        "te_field_name": self.timeedit.get_field_defs(f)["name"],
                        "canvas_group": cg,
                    }
                )

            return template_config
        except NoDataFound:
            return "", 404

    delete_parser = reqparse.RequestParser()
    delete_parser.add_argument("id", type=str, required=True)
    delete_parser.add_argument("canvas_group", type=str, required=True)
    delete_parser.add_argument("X-LTI-ROLES", location="headers")

    @ns.param("id", "Config template id")
    @ns.param("canvas_group", "Canvas group")
    @ns.response(204, "Config template deleted")
    @ns.response(404, "Config template not found")
    def delete(self):
        args = self.delete_parser.parse_args(strict=True)
        if args.id == "default" and not _is_admin(args.get("X-LTI-ROLES")):
            return "", 403
        try:
            self.db.delete_template_config(args.id)
            return "", 204
        except NoDataFound:
            return {"message": "Connection not found."}, 404

    post_parser = reqparse.RequestParser()
    post_parser.add_argument("config_type", type=str, required=True)
    post_parser.add_argument("te_type", type=str, required=True)
    post_parser.add_argument("te_field", type=str, required=True)
    post_parser.add_argument("canvas_group", type=str, required=True)
    post_parser.add_argument("default", type=str, required=True)
    post_parser.add_argument("X-LTI-ROLES", location="headers")

    @ns.param("config_type", "title | location | description")
    @ns.param("te_type", "Timeedit object type")
    @ns.param("te_field", "Object type field")
    @ns.param("canvas_group", "Canvas group")
    @ns.param("default", "Add to default template")
    @ns.response(204, "Config template added")
    @ns.response(400, "Missing parameters")
    def post(self):
        args = self.post_parser.parse_args(strict=True)
        if args.default == "true" and not _is_admin(args.get("X-LTI-ROLES")):
            return "", 403
        canvas_group = "default" if args.default == "true" else args.canvas_group
        try:
            self.db.add_template_config(args.config_type, args.te_type, args.te_field, canvas_group)
            return "", 204
        except UniqueViolation:
            return {"message": "Type and field combination already exist"}, 400
