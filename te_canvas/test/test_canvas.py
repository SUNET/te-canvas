import unittest
import te_canvas.canvas as canvas


class TestCanvas(unittest.TestCase):

    def test_delete_event(self):
        try:
            canvas.delete_event(0)
        except Exception:
            self.fail()



if __name__ == '__main__':
    unittest.main()
