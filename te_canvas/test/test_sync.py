import logging
import unittest

import te_canvas.canvas as canvas
from te_canvas.app import App
from te_canvas.db import DB, Connection, Event, Test

CANVAS_GROUP = 169
TE_GROUP = "courseevt_te-canvas-test"

integration_test_event = {
    "title": "Föreläsning",
    "location_name": "Unit Test Room",
    "start_at": "2022-01-03T08:00:00Z",
    "end_at": "2022-01-03T09:00:00Z",
    "context_code": f"course_{CANVAS_GROUP}",
}


def dict_eq(superset: dict, subset: dict) -> bool:
    for key in subset:
        if not key in superset or superset[key] != subset[key]:
            return False
    return True


class TestSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):  # Performed once, before all tests
        # Setup
        db = DB(
            hostname="localhost",
            port="5433",
            username="test_user",
            password="test_password",
            database="test_db",
        )
        with db.sqla_session() as session:
            session.query(Connection).delete()
            session.query(Event).delete()
            session.query(Test).delete()

        canvas.delete_events_all(CANVAS_GROUP)

        cls.app = App(db)
        cls.app.logger.setLevel(logging.CRITICAL)

    def test_canvas_empty(self):
        """Test setup."""
        self.assertEqual(canvas.get_events_all(CANVAS_GROUP), [])

    def test_sync(self):
        """Test sync job."""
        # Add connection, perform sync
        with self.app.db.sqla_session() as session:
            session.add(Connection(canvas_group=CANVAS_GROUP, te_group=TE_GROUP))
        self.app.sync_job()

        # Check that...
        with self.app.db.sqla_session() as session:
            # There is one event added to the local DB
            self.assertEqual(session.query(Event).count(), 1)
            event_local = session.query(Event).one()

            # There is one event added to Canvas
            events = canvas.get_events_all(CANVAS_GROUP)
            self.assertEqual(len(events), 1)
            event_canvas = events[0]

            # Event data is as expected
            self.assertEqual(event_local.canvas_group, str(CANVAS_GROUP))
            self.assertTrue(dict_eq(vars(event_canvas), integration_test_event))

            # The local DB and Canvas event agree on ID
            self.assertEqual(event_local.canvas_id, str(event_canvas.id))

        # Re-run sync job and see that the event has a new ID on Canvas (i.e.
        # has been removed and re-added).
        # TODO: This behaviour might need to change to e.g. not break event URLs.
        event_old = events[0]
        self.app.sync_job()
        events = canvas.get_events_all(CANVAS_GROUP)
        self.assertEqual(len(events), 1)
        event_new = events[0]
        self.assertNotEqual(event_old.id, event_new.id)

        # TODO:
        # - Edit event on TE, run sync job.
        # - Remove event on TE, run sync job.

        # Flag connection for deletion, run sync_job again
        with self.app.db.sqla_session() as session:
            session.query(Connection).one().delete_flag = True
        self.app.sync_job()

        with self.app.db.sqla_session() as session:
            self.assertEqual(session.query(Connection).count(), 0)
            self.assertEqual(session.query(Event).count(), 0)
        events = canvas.get_events_all(CANVAS_GROUP)
        self.assertEqual(len(events), 0)
