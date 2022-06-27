import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from canvasapi import Canvas as CanvasAPI
from canvasapi.calendar_event import CalendarEvent
from canvasapi.course import Course
from canvasapi.exceptions import ResourceDoesNotExist

from te_canvas.log import get_logger
from te_canvas.translator import TAG_TITLE


class Canvas:
    def __init__(self):
        self.logger = get_logger()
        try:
            url = os.environ["CANVAS_URL"]
            key = os.environ["CANVAS_KEY"]
        except Exception as e:
            self.logger.critical(f"Missing env var: {e}")
            sys.exit(1)

        self.canvas = CanvasAPI(url, key)

    # ---- Courses -------------------------------------------------------------

    def get_courses(self) -> list[Course]:
        """
        Get all courses.
        """
        root_user = self.canvas.get_account(1)
        res = list(root_user.get_courses())
        if len(res) == 0:
            self.logger.warning("canvas.get_courses() returned 0 courses.")
        return res

    # ---- Events --------------------------------------------------------------

    def get_events(self, course: int) -> list[CalendarEvent]:
        """
        Get all tagged events for a course.
        """
        return [
            e
            for e in self.canvas.get_calendar_events(
                context_codes=[f"course_{course}"],
                all_events=True,
            )
            if e.title.endswith(TAG_TITLE)
        ]

    def create_event(self, event: dict) -> CalendarEvent:
        """
        Create a calendar event.

        Returns:
            The created event.
        """
        return self.canvas.create_calendar_event(event)

    def delete_event(self, event: CalendarEvent) -> Optional[CalendarEvent]:
        """
        Delete a tagged Canvas event.

        If the event does not exist on Canvas, this is a NOOP and no exception is raised.

        Returns:
            The deleted event or None.
        """
        if (not event.title.endswith(TAG_TITLE)) or (event.workflow_state == "deleted"):
            return None
        try:
            event.delete()
            return event
        except ResourceDoesNotExist:
            return None

    def delete_events(self, course: int) -> list[CalendarEvent]:
        """
        Delete all tagged events.

        Returns:
            List of deleted events.
        """
        events = self.get_events(course)
        res = []
        for e in events:
            if self.delete_event(e) is not None:
                res.append(e)
        return res

    # ---- Not used in main program, just for utility scripts ------------------

    def delete_events_parallel(self, course: int, max_workers: int) -> list[CalendarEvent]:
        """
        Delete all tagged events using concurrent API calls.

        Returns:
            List of deleted events.
        """
        events = self.get_events(course)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            res = executor.map(self.delete_event, events)
        return list(filter(None, res)) # Filter out None results (non deleted events)
