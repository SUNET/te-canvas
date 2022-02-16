import os

from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api

from te_canvas.api.canvas import canvas_api
from te_canvas.api.connection import connection_api, ConnectionApi
from te_canvas.api.timeedit import timeedit_api
from te_canvas.api.version import version_api
from te_canvas.log import get_logger
from te_canvas.db import DB


class App:
    def __init__(self, db):
        self.logger = get_logger()

        self.db = db

        self.flask = Flask(__name__)
        self.flask.config["SECRET_KEY"] = os.urandom(128)

        CORS(self.flask, resources={r"/api/*": {"origins": "*"}})

        api = Api(self.flask, prefix="/api")
        api.add_namespace(version_api)
        api.add_namespace(timeedit_api)
        api.add_namespace(canvas_api)

        connection_api.add_resource(ConnectionApi, "", resource_class_kwargs={"db": db})
        api.add_namespace(connection_api)

        @self.flask.after_request
        def log_request(response):
            self.logger.info(
                "[API] Method: {}, Status: {}, URL: {}, JSON: {}".format(
                    request.method, response.status_code, request.url, request.json
                )
            )
            return response

app = App(DB())
