import os
import sys

from canvasapi import Canvas

from te_canvas.log import get_logger

logger = get_logger()

try:
    url = os.environ['CANVAS_URL']
    key = os.environ['CANVAS_KEY']
except Exception as e:
    logger.debug(f'Failed to load configuration: {e}')
    sys.exit(-1)

canvas = Canvas(url, key)


def get_all_courses():
    root_user = canvas.get_account(1)
    return list(root_user.get_courses())


def create_event(event):
    return canvas.create_calendar_event(event)


def delete_event(id):
    # TODO: Do this using one request
    return canvas.get_calendar_event(id).delete()
