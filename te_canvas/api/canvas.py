from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import DBAPIError

from te_canvas.canvas import get_courses_all
import te_canvas.log as log

logger = log.get_logger()

canvas_api = Namespace(
    'canvas',
    description='API for getting data from Canvas',
    prefix='/api',
)


class CanvasApi(Resource):
    def get(self):
        return [c.id for c in get_courses_all()]


canvas_api.add_resource(CanvasApi, '')
