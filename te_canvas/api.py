import os

from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api

import te_canvas.api_ns.canvas as canvas_api
import te_canvas.api_ns.config as config_api
import te_canvas.api_ns.connection as connection_api
import te_canvas.api_ns.timeedit as timeedit_api
import te_canvas.api_ns.version as version_api
from te_canvas.canvas import Canvas
from te_canvas.db import DB
from te_canvas.log import get_logger
from te_canvas.timeedit import TimeEdit


def create_app(db: DB = None, timeedit: TimeEdit = None, canvas: Canvas = None) -> Flask:
    db = db or DB()
    canvas = canvas or Canvas()
    timeedit = timeedit or TimeEdit()

    flask = Flask(__name__)
    flask.config["SECRET_KEY"] = os.urandom(128)

    CORS(flask)

    # TODO: More standard option for logging request, e.g. werkzeug logger?
    logger = get_logger()

    @flask.after_request
    def log_request(response):
        logger.info("[API] Method: {}, Status: {}, URL: {}".format(request.method, response.status_code, request.url))
        return response

    api = Api(flask, prefix="/api")

    # --- Version --------------------------------------------------------------

    version_api.ns.add_resource(version_api.Version, "")
    api.add_namespace(version_api.ns)

    # --- TimeEdit -------------------------------------------------------------

    timeedit_api.ns.add_resource(timeedit_api.Objects, "/objects", resource_class_kwargs={"timeedit": timeedit})
    timeedit_api.ns.add_resource(timeedit_api.Object, "/object", resource_class_kwargs={"timeedit": timeedit})
    timeedit_api.ns.add_resource(timeedit_api.Types, "/types", resource_class_kwargs={"timeedit": timeedit})
    timeedit_api.ns.add_resource(timeedit_api.Fields, "/fields", resource_class_kwargs={"timeedit": timeedit})
    api.add_namespace(timeedit_api.ns)

    # --- Canvas ---------------------------------------------------------------

    canvas_api.ns.add_resource(canvas_api.Courses, "/courses", resource_class_kwargs={"canvas": canvas})
    api.add_namespace(canvas_api.ns)

    # --- Connection -----------------------------------------------------------

    connection_api.ns.add_resource(connection_api.Connection, "", resource_class_kwargs={"db": db})
    api.add_namespace(connection_api.ns)

    # --- Config ---------------------------------------------------------------

    config_api.ns.add_resource(config_api.Template, "/template", resource_class_kwargs={"db": db})
    config_api.ns.add_resource(config_api.Ok, "/ok", resource_class_kwargs={"db": db})
    api.add_namespace(config_api.ns)

    return flask


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
