import os

from te_canvas import app
from te_canvas.log import get_logger
from te_canvas.job import JobScheduler
from te_canvas.sync import sync_job

os.environ["PYTHONPATH"] = os.getcwd()
logger = get_logger()


def get_app():
    return app.app


logger.debug("TE - Canvas sync API is starting...")

jobs = JobScheduler(nr_threads=10)
jobs.add(sync_job, 10, {})
jobs.start()

# ASSUME: When a job raises an exception this is logged and swallowed (does not affect next run).
# TODO: Verify this.

if __name__ == "__main__":
    get_app().run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
else:
    te_canvas_app = get_app()
