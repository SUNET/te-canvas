import logging
import unittest
from typing import Optional

from te_canvas.canvas import Canvas
from te_canvas.db import DB, Config, Connection, Event, Test
from te_canvas.sync import Syncer

CANVAS_GROUP = 169
TE_GROUP = "fullroom_unittest"

integration_test_event = {
    "title": "Test title​",
    "location_name": "--> Unit Test Room <--",
    "start_at": "2022-10-01T10:00:00Z",
    "end_at": "2022-10-01T11:00:00Z",
    "context_code": f"course_{CANVAS_GROUP}",
}


# Check that subset is a subset of superset. Return a string describing the first differing key, or None.
def dict_eq(superset: dict, subset: dict) -> Optional[str]:
    for key in subset:
        if not key in superset:
            return f"{key} not in superset"
        if superset[key] != subset[key]:
            return f"{key}: superset: {superset[key]}, subset: {subset[key]}"
    return None


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
            session.query(Config).delete()

            # Event template strings, needed to perform a sync
            session.add(Config(key="title", value="Test title"))
            session.add(Config(key="location", value="--> ${room::room.name} <--"))
            session.add(Config(key="description", value="Test description"))

        cls.sync = Syncer(db)
        cls.sync.logger.setLevel(logging.CRITICAL)

        cls.canvas = Canvas()
        for event in cls.canvas.get_events_all(CANVAS_GROUP):
            cls.canvas.delete_event(event.id)

        logging.disable()

    def test_canvas_empty(self):
        """Test setup."""
        self.assertEqual(self.canvas.get_events_all(CANVAS_GROUP), [])

    def test_sync(self):
        """Test sync job."""
        # Add connection, perform sync
        with self.sync.db.sqla_session() as session:
            session.add(Connection(canvas_group=CANVAS_GROUP, te_group=TE_GROUP))
        self.sync.sync_all()

        # Check that...
        with self.sync.db.sqla_session() as session:
            # There is one event added to the local DB
            self.assertEqual(session.query(Event).count(), 1)
            event_local = session.query(Event).one()

            # There is one event added to Canvas
            events = self.canvas.get_events_all(CANVAS_GROUP)
            self.assertEqual(len(events), 1)
            event_canvas = events[0]

            # Event data is as expected
            self.assertEqual(event_local.canvas_group, str(CANVAS_GROUP))
            self.assertEqual(dict_eq(vars(event_canvas), integration_test_event), None)

            # The local DB and Canvas event agree on ID
            self.assertEqual(event_local.canvas_id, str(event_canvas.id))

        # Re-run sync job and see that the event has not been removed and re-added
        event_old = events[0]
        self.sync.sync_all()
        events = self.canvas.get_events_all(CANVAS_GROUP)
        self.assertEqual(len(events), 1)
        event_new = events[0]
        self.assertEqual(event_old.id, event_new.id)

        # TODO:
        # - Edit event on TE, run sync job.
        # - Add event on TE, run sync job.
        # - Remove event on TE, run sync job.

        # Flag connection for deletion, run sync_job again
        with self.sync.db.sqla_session() as session:
            session.query(Connection).one().delete_flag = True
        self.sync.sync_all()

        with self.sync.db.sqla_session() as session:
            self.assertEqual(session.query(Connection).count(), 0)
            self.assertEqual(session.query(Event).count(), 0)
        events = self.canvas.get_events_all(CANVAS_GROUP)
        self.assertEqual(len(events), 0)
