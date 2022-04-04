import os
import unittest

from te_canvas.db import DB, Test, flat_list


class UnittestException(Exception):
    pass


class TestDB(unittest.TestCase):
    def test_init_env_vars(self):
        """Initalizing database with env vars."""
        os.environ["POSTGRES_HOSTNAME"] = "localhost"
        os.environ["POSTGRES_PORT"] = "5433"
        os.environ["POSTGRES_USER"] = "test_user"
        os.environ["POSTGRES_PASSWORD"] = "test_password"
        os.environ["POSTGRES_DB"] = "test_db"
        db = DB()
        self.assertEqual(
            db.conn_str,
            "postgresql+psycopg2://test_user:test_password@localhost:5433/test_db",
        )

    def test_init_kwargs(self):
        """Initalizing database with kwargs."""
        os.environ["POSTGRES_HOSTNAME"] = "a"
        os.environ["POSTGRES_PORT"] = "b"
        os.environ["POSTGRES_USER"] = "c"
        os.environ["POSTGRES_PASSWORD"] = "d"
        os.environ["POSTGRES_DB"] = "e"
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
