import os
import sys
import unittest

from te_canvas.db import DB, Connection, Event, Test, flat_list


class UnittestException(Exception):
    pass


class TestDB(unittest.TestCase):
    def test_init_env_vars(self):
        """Initalizing database with env vars."""
        os.environ["TE_CANVAS_DB_HOSTNAME"] = "localhost"
        os.environ["TE_CANVAS_DB_PORT"] = "5433"
        os.environ["TE_CANVAS_DB_USERNAME"] = "test_user"
        os.environ["TE_CANVAS_DB_PASSWORD"] = "test_password"
        os.environ["TE_CANVAS_DB_DATABASE"] = "test_db"
        db = DB()
        self.assertEqual(
            db.conn_str,
            "postgresql+psycopg2://test_user:test_password@localhost:5433/test_db",
        )

    def test_init_kwargs(self):
        """Initalizing database with kwargs."""
        os.environ["TE_CANVAS_DB_HOSTNAME"] = "a"
        os.environ["TE_CANVAS_DB_PORT"] = "b"
        os.environ["TE_CANVAS_DB_USERNAME"] = "c"
        os.environ["TE_CANVAS_DB_PASSWORD"] = "d"
        os.environ["TE_CANVAS_DB_DATABASE"] = "e"
        db = DB(
            hostname="localhost",
            port="5433",
            username="test_user",
            password="test_password",
            database="test_db",
        )
        self.assertEqual(
            db.conn_str,
            "postgresql+psycopg2://test_user:test_password@localhost:5433/test_db",
        )

    def test_sqla_session(self):
        """Test commit and rollback functionality."""
        # Set up a database with one entry
        db = DB(
            hostname="localhost",
            port="5433",
            username="test_user",
            password="test_password",
            database="test_db",
        )
        with db.sqla_session() as session:
            session.query(Test).delete()
            session.add(Test())
        with db.sqla_session() as session:
            self.assertEqual(flat_list(session.query(Test.foo)), ["bar"])

        # Attempt to add an entry, but cancel and rollback due to exception
        try:
            with db.sqla_session() as session:
                session.add(Test(foo="baz"))
                raise UnittestException  # This will be caught by db.sqla_session, which rolls back and re-raises
        except UnittestException:  # So we must catch it also in an outer scope
            pass
        with db.sqla_session() as session:
            self.assertEqual(flat_list(session.query(Test.foo)), ["bar"])

        # Clean up
        with db.sqla_session() as session:
            session.query(Test).delete()
            self.assertEqual(flat_list(session.query(Test.foo)), [])


if __name__ == "__main__":
    unittest.main()
