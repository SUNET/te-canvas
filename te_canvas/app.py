import os

from flask_cors import CORS
from flask import Flask, request
from flask_restx import Api
from te_canvas.api.version import version_api
from te_canvas.log import get_logger

logger = get_logger()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(128)

cors = CORS(app,
            resources={r"/api/*": {"origins": "*"}})

api = Api(app, prefix='/api')
api.add_namespace(version_api)


@app.after_request
def log_request(response):
    logger.info('[API] Method: {}, Status: {}, URL: {}, JSON: {}'.format(
        request.method, response.status_code, request.url, request.json))
    return response
