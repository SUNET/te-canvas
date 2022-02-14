from flask import request
from flask_restx import Resource, Namespace, fields, reqparse
from sqlalchemy.exc import DBAPIError

from te_canvas.canvas import get_courses_all
import te_canvas.log as log

logger = log.get_logger()

canvas_api = Namespace(
    "canvas",
    description="API for getting data from Canvas",
    prefix="/api",
)


class Courses(Resource):
    def get(self):
        try:
            data = get_courses_all()
        except Exception:
            return {"status": "failure"}, 500
        return {"status": "success", "data": [c.id for c in data]}


canvas_api.add_resource(Courses, "/courses")
