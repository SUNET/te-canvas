from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import DBAPIError

from te_canvas.te import course_instances, course_instances_all
import te_canvas.log as log

logger = log.get_logger()

timeedit_api = Namespace(
    'timeedit',
    description='API for getting data from TimeEdit',
    prefix='/api',
)


class TimeEditApi(Resource):
    pagination_parser = reqparse.RequestParser()
    pagination_parser.add_argument('number_of_objects', type=int)
    pagination_parser.add_argument('begin_index', type=int)

    @timeedit_api.param(
        'number_of_objects', 'Number of course instances to return, max 1000.'
    )
    @timeedit_api.param(
        'begin_index', 'Starting index of requested course instance sequence.'
    )
    def get(self):
        args = self.pagination_parser.parse_args()
        n = args['number_of_objects']
        i = args['begin_index']
        if n or i:
            return course_instances(n or 1000, i or 0)
        return course_instances_all()


timeedit_api.add_resource(TimeEditApi, '')
