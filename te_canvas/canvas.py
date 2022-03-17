import os
import sys

from canvasapi import Canvas as CanvasAPI
from canvasapi.calendar_event import CalendarEvent
from canvasapi.exceptions import ResourceDoesNotExist

from te_canvas.log import get_logger


class Canvas:
    def __init__(self):
        self.logger = get_logger()
        try:
            url = os.environ["CANVAS_URL"]
            key = os.environ["CANVAS_KEY"]
        except Exception as e:
            self.logger.critical(f"Failed to load configuration: {e}")
            sys.exit(-1)

        self.canvas = CanvasAPI(url, key)

    def get_courses_all(self):
        root_user = self.canvas.get_account(1)
        res = list(root_user.get_courses())
        if len(res) == 0:
            self.logger.warning("canvas.get_courses_all() returned 0 courses.")
        return res

    def create_event(self, event: dict) -> CalendarEvent:
        return self.canvas.create_calendar_event(event)

    # If the event does not exist on Canvas, this is a NOOP and no exception is
    # raised.
    def delete_event(self, id: int):
        try:
            self.canvas.get_calendar_event(id).delete()
        except ResourceDoesNotExist:
            pass

    # NOTE: The following two functions used only for testing.

    def get_events_all(self, course: int):
        return list(
            self.canvas.get_calendar_events(
                context_codes=[f"course_{course}"],
                start_date="2022-01-01",
                end_date="2032-01-01",
            )
        )

    def delete_events_all(self, course: int):
        for event in self.get_events_all(course):
            self.delete_event(event.id)
