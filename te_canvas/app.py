import os

from flask_cors import CORS
from flask import Flask
from flask_restx import Api
from te_canvas.api.version import version_api

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(128)

cors = CORS(app,
            resources={r"/api/*": {"origins": "*"}})

api = Api(app, prefix='/api')
api.add_namespace(version_api)
