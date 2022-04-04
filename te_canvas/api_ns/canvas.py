from flask_restx import Namespace, Resource

import te_canvas.log as log
from te_canvas.canvas import Canvas

logger = log.get_logger()

ns = Namespace(
    "canvas",
    description="API for getting data from Canvas",
    prefix="/api",
)


class Courses(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.canvas = kwargs["canvas"]

    def get(self):
        data = self.canvas.get_courses_all()
        return [c.id for c in data]
