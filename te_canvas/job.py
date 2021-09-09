from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from te_canvas.log import get_logger

logger = get_logger()


class JobScheduler(object):
    def __init__(self, nr_threads=10):
        self._scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(nr_threads)},
            jobstores={'default': MemoryJobStore()},
            job_defaults={},
            timezone=utc
        )

    def get(self):
        return self._scheduler

    def start(self):
        logger.debug('[JobScheduler] Starting scheduler.')
        return self._scheduler.start()

    def stop(self):
        logger.debug('[JobScheduler] Stopping scheduler.')
        return self._scheduler.shutdown()

    def add(self, func, seconds, kwargs):
        logger.debug(
            f'[JobScheduler] Adding job to scheduler: interval={seconds}')
        return self._scheduler.add_job(func, 'interval', seconds=seconds,
                                       kwargs=kwargs)
