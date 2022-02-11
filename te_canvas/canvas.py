import os
import sys

from canvasapi import Canvas
from canvasapi.calendar_event import CalendarEvent

from te_canvas.log import get_logger

logger = get_logger()

try:
    url = os.environ["CANVAS_URL"]
    key = os.environ["CANVAS_KEY"]
except Exception as e:
    logger.debug(f"Failed to load configuration: {e}")
    sys.exit(-1)

canvas = Canvas(url, key)


def get_courses_all():
    try:
        root_user = canvas.get_account(1)
        courses = list(root_user.get_courses())
    except Exception:
        logger.error("Failed to get account 1 courses from Canvas.")
        return None

    return courses


def create_event(event) -> CalendarEvent:
    return canvas.create_calendar_event(event)


def delete_event(id):
    return canvas.get_calendar_event(id).delete()
