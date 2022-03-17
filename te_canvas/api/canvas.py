from flask_restx import Namespace, Resource

import te_canvas.log as log
from te_canvas.canvas import Canvas

logger = log.get_logger()

canvas_api = Namespace(
    "canvas",
    description="API for getting data from Canvas",
    prefix="/api",
)

canvas = Canvas()


class Courses(Resource):
    def get(self):
        data = canvas.get_courses_all()
        return [c.id for c in data]


canvas_api.add_resource(Courses, "/courses")
