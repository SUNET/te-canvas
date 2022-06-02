import unittest

from te_canvas.timeedit import TimeEdit

# NOTE: Most of these depend on specific TE installation so should be considered integration tests.


class TestTE(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timeedit = TimeEdit()

    def test_find_types_all(self):
        """find_types_all should return at least one course."""
        types = self.timeedit.find_types_all()
        self.assertGreater(len(types), 0, "find_types_all should return at least one course.")
        # Don't know how meaningful it is to add these sorts of tests...
        # Perhaps just throw an exception if no reservations are found, since this could point to
        # some issue (unless the schedule is entirely new).

    def test_find_objects_all(self):
        """The function find_objects_all should handle pagination correctly.

        NOTE: Not meaningful if there are fewer than 1000 'courseevt' in TE.
        """
        first_10_courseevt = self.timeedit.find_objects("courseevt", 10, 1040, None)
        all_courseevt = self.timeedit.find_objects_all("courseevt", None)
        self.assertEqual(first_10_courseevt, all_courseevt[1040:1050])

    def test_find_reservations_all_empty(self):
        """find_reservations_all should handle the empty list properly."""
        reservations = self.timeedit.find_reservations_all([], {})
        self.assertEqual(reservations, [])

    # Commented out just to simplify TimeEdit setup, but still true.
    # def test_find_reservations_all_multiple_same_type(self):
    #     """find_reservations_all should not rely on there being only one object of each type."""
    #     reservations = self.timeedit.find_reservations_all(["fullroom_unittest"], {})
    #     self.assertEqual(len([True for f in reservations[0]["objects"] if f["type"] == "room"]), 2)


if __name__ == "__main__":
    unittest.main()
