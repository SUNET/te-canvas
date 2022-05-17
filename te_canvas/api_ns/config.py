from flask_restx import Namespace, Resource, reqparse
from sqlalchemy.exc import NoResultFound

ns = Namespace("config", description="Config API", prefix="/api")


class Config(Resource):

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.db = kwargs["db"]

    get_parser = reqparse.RequestParser()
    get_parser.add_argument("key", type=str, required=True)

    @ns.param("key", "Key")
    def get(self):
        args = self.get_parser.parse_args(strict=True)
        try:
            return self.db.get_config(args.key)
        except NoResultFound:
            return "", 404

    put_parser = reqparse.RequestParser()
    put_parser.add_argument("key", type=str, required=True)
    put_parser.add_argument("value", type=str, required=True)

    @ns.param("key", "Key")
    @ns.param("value", "Value")
    def put(self):
        args = self.put_parser.parse_args(strict=True)
        self.db.set_config(args.key, args.value)
