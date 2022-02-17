from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from sqlalchemy.exc import DBAPIError

import te_canvas.log as log
from te_canvas.canvas import get_courses_all

logger = log.get_logger()

canvas_api = Namespace(
    "canvas",
    description="API for getting data from Canvas",
    prefix="/api",
)


class Courses(Resource):
    def get(self):
        data = get_courses_all()
        return [c.id for c in data]


canvas_api.add_resource(Courses, "/courses")
