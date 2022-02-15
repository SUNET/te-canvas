from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from te_canvas.log import get_logger

logger = get_logger()


class JobScheduler(object):
    def __init__(self):
        self._scheduler = BackgroundScheduler(timezone=utc)

    def get(self):
        return self._scheduler

    def start(self):
        logger.debug("[JobScheduler] Starting scheduler.")
        return self._scheduler.start()

    def stop(self):
        logger.debug("[JobScheduler] Stopping scheduler.")
        return self._scheduler.shutdown()

    def add(self, func, seconds, kwargs):
        logger.debug(f"[JobScheduler] Adding job to scheduler: interval={seconds}")
        return self._scheduler.add_job(func, "interval", seconds=seconds, kwargs=kwargs)
