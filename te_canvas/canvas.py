import os
import sys

from canvasapi import Canvas

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


def create_event(event):
    try:
        calendar_event = canvas.create_calendar_event(event)
    except Exception:
        logger.error("Failed to create calendar event on Canvas.")
        return None

    return calendar_event


def delete_event(id):
    # TODO: Do this using one request
    try:
        calendar_event = canvas.get_calendar_event(id).delete()
    except Exception:
        logger.error("Failed to remove calendar event from Canvas.")
        return None

    return calendar_event
