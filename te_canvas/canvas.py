import os
import sys

from canvasapi import Canvas
from canvasapi.calendar_event import CalendarEvent
from canvasapi.exceptions import ResourceDoesNotExist

from te_canvas.log import get_logger

logger = get_logger()

try:
    url = os.environ["CANVAS_URL"]
    key = os.environ["CANVAS_KEY"]
except Exception as e:
    logger.critical(f"Failed to load configuration: {e}")
    sys.exit(-1)

canvas = Canvas(url, key)


def get_courses_all():
    root_user = canvas.get_account(1)
    return list(root_user.get_courses())


def create_event(event: dict) -> CalendarEvent:
    return canvas.create_calendar_event(event)


# If the event does not exist on Canvas, this is a NOOP and no exception is
# raised.
def delete_event(id: int):
    try:
        canvas.get_calendar_event(id).delete()
    except ResourceDoesNotExist:
        pass
