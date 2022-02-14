from flask import request
from flask_restx import Resource, Namespace


version_api = Namespace("version", description="Version API", prefix="/api")


class VersionApi(Resource):
    def get(self):
        return "v0.0.1"


version_api.add_resource(VersionApi, "")
