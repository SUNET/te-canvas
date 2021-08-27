import os

from te_canvas import app
from te_canvas.log import get_logger

os.environ['PYTHONPATH'] = os.getcwd()
logger = get_logger()


def get_app():
    return app.app


logger.debug('TE - Canvas sync API is starting...')

if __name__ == '__main__':
    get_app().run(debug=True, host='0.0.0.0', port=5000)
else:
    te_canvas_app = get_app()
