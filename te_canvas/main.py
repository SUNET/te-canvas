import os

from te_canvas.app import app
from te_canvas.log import get_logger
from te_canvas.job import JobScheduler
from te_canvas.sync import sync_job

os.environ["PYTHONPATH"] = os.getcwd()
logger = get_logger()

logger.debug("TE - Canvas sync API is starting...")

jobs = JobScheduler()
jobs.add(sync_job, 10, {})
jobs.start()

if __name__ == "__main__":
    app.flask.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
