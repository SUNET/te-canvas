from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import DBAPIError

import te_canvas.db.model as db
import te_canvas.log as log

logger = log.get_logger()

connection_api = Namespace(
    'connection',
    description='API for handling connections between TimeEdit and Canvas',
    prefix='/api',
)

# (?): Not RESTful to use a single endpoint with IDs in query string?
class ConnectionApi(Resource):

    # NOTE: Will be deprecated in flask-restx 2.0
    id_parser = reqparse.RequestParser()
    id_parser.add_argument('te_group', type=str, required=True)
    id_parser.add_argument('canvas_group', type=str, required=True)

    @connection_api.param('te_group', 'TimeEdit group ID')
    @connection_api.param('canvas_group', 'Canvas group ID')
    def post(self):
        args = self.id_parser.parse_args(strict=True)
        try:
            db.add_connection(args.te_group, args.canvas_group)
        except DBAPIError as e:
            logger.error(e)
            return {'status': 'failure'}, 500
        return {'status': 'success'}

    @connection_api.param('te_group', 'TimeEdit group ID')
    @connection_api.param('canvas_group', 'Canvas group ID')
    def delete(self):
        args = self.id_parser.parse_args(strict=True)
        try:
            db.delete_connection(args.te_group, args.canvas_group)
        except db.DeleteEmpty:
            return {'status': 'unchanged', 'message': 'Connection not found.'}
            # (?): Also return a different status code than 200?
        except DBAPIError as e:
            logger.error(e)
            return {'status': 'failure'}, 500
        return {'status': 'success'}

    def get(self):
        try:
            return [
                {'te_group': x, 'canvas_group': y}
                for (x, y) in db.get_connections()
            ]
        except DBAPIError as e:
            logger.error(e)
            return {'status': 'failure'}, 500


connection_api.add_resource(ConnectionApi, '')
