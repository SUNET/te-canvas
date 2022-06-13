import os
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile

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

    # Courses

    def get_courses(self) -> list[Course]:
        """
        Get all courses.
        """
        root_user = self.canvas.get_account(1)
        res = list(root_user.get_courses())
        if len(res) == 0:
            self.logger.warning("canvas.get_courses() returned 0 courses.")
        return res

    # Events

    def get_events(self, course: int) -> list[CalendarEvent]:
        """
        Get all tagged events for a course.
        """
        return [
            e
            for e in self.canvas.get_calendar_events(
                context_codes=[f"course_{course}"],
                start_date="2022-01-01",
                end_date="2032-01-01",
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

    def delete_event(self, event: CalendarEvent) -> None:
        """
        Delete a tagged Canvas event.

        If the event does not exist on Canvas, this is a NOOP and no exception is raised.
        """
        if (not event.title.endswith(TAG_TITLE)) or (event.workflow_state == "deleted"):
            return
        try:
            event.delete()
        except ResourceDoesNotExist:
            pass

    def delete_events(self, course: int) -> None:
        """
        Delete all tagged events.
        """
        events = self.get_events(course)
        for e in events:
            self.delete_event(e)

    # --- NOT USED IN MAIN PROGRAM, JUST FOR UTILITY SCRIPTS ---

    def clear_events_tagged(self, course: int, max_workers: int):
        """
        Recovery method to clear all Canvas events without using the event database.

        Goes through all Canvas events and removes all whose title ends with Translator.EVENT_TAG.
        """
        events = self.get_events(course)

        tmp = NamedTemporaryFile(delete=False)
        pickle.dump(events, tmp)
        tmp.close()
        self.logger.info(f"Events backup pickled to {tmp.name}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.__clear_events_tagged_helper, events)

    def __clear_events_tagged_helper(self, event):
        if event.title.endswith(TAG_TITLE):
            self.logger.info(f"Deleting {event.id}")
            self.delete_event(event.id)
