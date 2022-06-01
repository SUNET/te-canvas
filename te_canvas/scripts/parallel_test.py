# Usage:
# python parallel_test.py <course> <no_threads>

# Experminenting with this found that 60 concurrent calls to create_event are ok.
# TODO: Check with other canvasapi methods we use, e.g. get_calendar_events

import sys
import threading

from te_canvas.canvas import Canvas
from te_canvas.translator import TAG_TITLE

c = Canvas()


def make_event(course):
    c.create_event(
        {
            "title": "Parallelization test event" + TAG_TITLE,
            "location_name": "location",
            "description": "description",
            "start_at": "20220601T120000",
            "end_at": "20220601T130000",
            "context_code": f"course_{course}",
        }
    )


if __name__ == "__main__":
    for i in range(int(sys.argv[2])):
        x = threading.Thread(target=make_event, args=(sys.argv[1],))
        x.start()
