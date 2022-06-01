# Usage:
# python clear_events.py <course> <n_threads>

import sys

from te_canvas.canvas import Canvas

if __name__ == "__main__":
    Canvas().clear_events_tagged(int(sys.argv[1]), int(sys.argv[2]))
