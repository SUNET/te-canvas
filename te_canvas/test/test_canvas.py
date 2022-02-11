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
    print(f"Failed to load configuration: {e}")
    sys.exit(-1)

canvas = canvasapi.Canvas(url, key)

class TestCanvas(unittest.TestCase):
    def test_delete_event(self):
        id = 0

        with self.assertRaises(canvasapi.exceptions.ResourceDoesNotExist):
            canvas.get_calendar_event(id)

        try:
            te_canvas.canvas.delete_event(id)
        except Exception:
            self.fail()


if __name__ == "__main__":
    unittest.main()
