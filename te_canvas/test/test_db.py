import os
import unittest

from sqlalchemy.exc import NoResultFound  # type: ignore

from te_canvas.db import DB, Config, Test, flat_list


class UnittestException(Exception):
    pass


class TestDB(unittest.TestCase):
    def setUp(self):
        self.environ_saved = dict(os.environ)

    def tearDown(self):
        os.environ = self.environ_saved

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

    def test_init_env_vars_missing(self):
        """Initalizing database with env vars, some missing."""
        if "POSTGRES_DB" in os.environ:
            del os.environ["POSTGRES_DB"]

        with self.assertRaises(SystemExit) as cm:
            db = DB()
        self.assertEqual(cm.exception.code, 1)

    def test_init_env_vars_missing_kwargs(self):
        """Initalizing database with kwargs, some env vars missing."""
        if "POSTGRES_DB" in os.environ:
            del os.environ["POSTGRES_DB"]

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

    def test_set_get_config(self):
        """Test config setter/getter with non-existing and existing keys."""
        db = DB(
            hostname="localhost",
            port="5433",
            username="test_user",
            password="test_password",
            database="test_db",
        )
        with db.sqla_session() as session:
            session.query(Config).delete()
            self.assertEqual(flat_list(session.query(Config)), [])

        with self.assertRaises(NoResultFound):
            db.get_config("foo")

        db.set_config("foo", "bar")
        self.assertEqual(db.get_config("foo"), "bar")

        db.set_config("foo", "baz")
        self.assertEqual(db.get_config("foo"), "baz")

        db.delete_config("foo")
        with self.assertRaises(NoResultFound):
            db.get_config("foo")

        db.delete_config("foo")


if __name__ == "__main__":
    unittest.main()
