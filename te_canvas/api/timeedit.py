from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import DBAPIError

from te_canvas.te import get_objects, get_objects_all
import te_canvas.log as log

logger = log.get_logger()

timeedit_api = Namespace(
    'timeedit',
    description='API for getting data from TimeEdit',
    prefix='/api',
)


class TimeEditApi(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('type', type=str, required=True)
    parser.add_argument('number_of_objects', type=int)
    parser.add_argument('begin_index', type=int)

    @timeedit_api.param('type', 'Type of object to get.')
    @timeedit_api.param(
        'number_of_objects', 'Number of objects to return, max 1000.'
    )
    @timeedit_api.param(
        'begin_index', 'Starting index of requested object sequence.'
    )
    def get(self):
        args = self.parser.parse_args(strict=True)
        type = args['type']
        n = args['number_of_objects']
        i = args['begin_index']
        if n or i:
            data = get_objects(type, n or 1000, i or 0)
        else:
            data = get_objects_all(type)

        return {
            'status': 'success',
            'data': data
        }


timeedit_api.add_resource(TimeEditApi, '')
