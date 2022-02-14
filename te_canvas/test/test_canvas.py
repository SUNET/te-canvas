import os
import sys
import unittest

import canvasapi
import canvasapi.exceptions

import te_canvas.canvas

try:
    url = os.environ["CANVAS_URL"]
    key = os.environ["CANVAS_KEY"]
except Exception as e:
    print(f"Failed to load configuration: {e}, exiting.")
    sys.exit(-1)

canvas = canvasapi.Canvas(url, key)

# NOTE: Statements are implicitly assumed to succeed, since they all should
# throw exceptions which (if they are not caught) register in the test results.


class TestCanvas(unittest.TestCase):
    def test_get_courses_all(self):
        """Getting all courses should succeed."""
        courses = te_canvas.canvas.get_courses_all()
        self.assertGreater(
            len(courses), 0, "get_courses_all should return at least one course."
        )

    def test_create_event_success(self):
        """Creating an event should succeed."""
        canvas_event = te_canvas.canvas.create_event(
            {
                "context_code": "course_168",  # Course "ernst_test"
                "title": "unittest_title",
                "location_name": "unittest_location",
                "description": "unittest_description",
                "start_at": "20220314T120000",
                "end_at": "20220314T130000",
            }
        )
        te_canvas.canvas.delete_event(canvas_event.id)

    def test_create_event_fail(self):
        """Creating an event should fail if the course does not exist."""
        with self.assertRaises(canvasapi.exceptions.ResourceDoesNotExist):
            te_canvas.canvas.create_event(
                {
                    "context_code": "course_9999",
                    "title": "unittest_title",
                    "location_name": "unittest_location",
                    "description": "unittest_description",
                    "start_at": "20220314T120000",
                    "end_at": "20220314T130000",
                }
            )

    def test_delete_event_non_existing(self):
        """Deleting a non-existing event should not cause an exception."""
        id = 0

        # Make sure that the event does not exist
        with self.assertRaises(canvasapi.exceptions.ResourceDoesNotExist):
            canvas.get_calendar_event(id)

        # Try to delete it anyway
        te_canvas.canvas.delete_event(id)


if __name__ == "__main__":
    unittest.main()
