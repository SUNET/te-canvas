from flask_restx import Namespace, Resource

ns = Namespace("version", description="Version API", prefix="/api")


class Version(Resource):
    def get(self):
        return "v0.0.1"
