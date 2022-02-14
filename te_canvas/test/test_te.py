import os
import sys
import unittest

import te_canvas.te

try:
    wsdl = os.environ["TE_WSDL_URL"]
    cert = os.environ["TE_CERT"]
    username = os.environ["TE_USERNAME"]
    password = os.environ["TE_PASSWORD"]
except Exception as e:
    print(f"Failed to load configuration: {e}, exiting.")
    sys.exit(-1)

# NOTE: Most of these depend on specific TE installation so should be considered integration tests.

class TestTE(unittest.TestCase):
    def test_find_types_all(self):
        """find_types_all should return at least one course."""
        types = te_canvas.te.find_types_all()
        self.assertGreater(len(types), 0, "find_types_all should return at least one course.")
        # Don't know how meaningful it is to add these sorts of tests...
        # Perhaps just throw an exception if no reservations are found, since
        # this could point to some issue (unless the schedule is entirely new).

    def test_find_objects_all(self):
        """The function find_objects_all should handle pagination correctly.

        NOTE: Not meaningful if there are fewer than 1000 'courseevt' in TE.
        """
        first_10_courseevt = te_canvas.te.find_objects("courseevt", 10, 1040, None)
        all_courseevt = te_canvas.te.find_objects_all("courseevt", None)
        self.assertEqual(first_10_courseevt, all_courseevt[1040:1050])

if __name__ == "__main__":
    unittest.main()
