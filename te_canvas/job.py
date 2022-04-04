from apscheduler.schedulers.background import BlockingScheduler
from pytz import utc

from te_canvas.log import get_logger
from te_canvas.sync import Sync

logger = get_logger()


class JobScheduler(object):
    def __init__(self):
        self.__scheduler = BlockingScheduler(timezone=utc)

    def get(self):
        return self.__scheduler

    def start(self):
        logger.info("Starting scheduler.")
        return self.__scheduler.start()

    def stop(self):
        logger.info("Stopping scheduler.")
        return self.__scheduler.shutdown()

    def add(self, func, seconds, kwargs):
        logger.info(f"Adding job to scheduler: interval={seconds}")
        return self.__scheduler.add_job(func, "interval", seconds=seconds, kwargs=kwargs)


if __name__ == "__main__":
    jobs = JobScheduler()
    jobs.add(Sync().sync_job, 10, {})
    jobs.start()
