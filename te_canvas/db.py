import logging
import os
import sys
from contextlib import contextmanager
from time import sleep
from typing import Optional

from psycopg2.errors import UniqueViolation
from sqlalchemy import Boolean, Column, String, create_engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from te_canvas.log import get_logger


def flat_list(query):
    return [r[0] for r in query]


Base = declarative_base()


class Connection(Base):
    # NOTE: For a given canvas_group C and te_group T, there can only be one
    # connection. Once a connection's delete flag has been set the connection
    # can not be modified, and a new connection (C, T) can not be added until
    # the old one is deleted by App.sync_job().
    __tablename__ = "connections"
    canvas_group = Column(String, primary_key=True)
    te_group = Column(String, primary_key=True)
    te_type = Column(String)
    delete_flag = Column(Boolean, default=False)


class Event(Base):
    __tablename__ = "events"
    canvas_id = Column(String, primary_key=True)
    te_id = Column(String, primary_key=True)
    canvas_group = Column(String)


# TODO: Can we avoid having this here and do this in test_db, perhaps
# dynamically in a test case? Not so important. But would be nice if this table
# is not included in the real database.
# Not really necessary, right? Since we use a separate test_db we can use any
# table for simple commit/rollback testing.
class Test(Base):
    __tablename__ = "unittest"
    foo = Column(String, primary_key=True, default="bar")


class DB:
    def __init__(self, **kwargs):
        logger = get_logger()

        env_var_mapping = {
            "hostname": "POSTGRES_HOSTNAME",
            "port": "POSTGRES_PORT",
            "username": "POSTGRES_USER",
            "password": "POSTGRES_PASSWORD",
            "database": "POSTGRES_DB",
        }

        try:
            env_vars = {k: os.environ[v] for (k, v) in env_var_mapping.items()}
        except KeyError as e:
            logger.critical(f"Missing env var: {e}")
            sys.exit(-1)

        conn = env_vars | kwargs

        self.conn_str = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
            conn["username"],
            conn["password"],
            conn["hostname"],
            conn["port"],
            conn["database"],
        )

        engine = create_engine(self.conn_str, pool_size=50, max_overflow=0)
        self.Session = sessionmaker(bind=engine)

        logging.getLogger("sqlalchemy.engine").addHandler(logger.handlers[0])
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

        while True:
            try:
                Base.metadata.create_all(engine)
                break
            except OperationalError:
                logger.info("Retrying database connection")
                sleep(1)

    @contextmanager
    def sqla_session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_connection(self, canvas_group: str, te_group: str, te_type: str):
        with self.sqla_session() as session:
            q = session.query(Connection).filter(
                Connection.te_group == te_group,
                Connection.canvas_group == canvas_group,
            )
            if q.count() == 0:
                session.add(Connection(canvas_group=canvas_group, te_group=te_group, te_type=te_type))
            else:
                if q.one().delete_flag:  # Will throw if q has > 1 row (invalid state)
                    raise DeleteFlagAlreadySet
                raise UniqueViolation

    def delete_connection(self, canvas_group: str, te_group: str):
        with self.sqla_session() as session:
            row = (
                session.query(Connection)
                .filter(
                    Connection.te_group == te_group,
                    Connection.canvas_group == canvas_group,
                )
                .one()
            )
            if row.delete_flag:
                raise DeleteFlagAlreadySet
            row.delete_flag = True

    def get_connections(self, canvas_group: Optional[str] = None) -> list[tuple[str, str, str, bool]]:
        with self.sqla_session() as session:
            # NOTE: We cannot return a list of Connection here, since the Session
            # they are connected to is closed at end of this block.
            query = session.query(Connection)

            if canvas_group is not None:
                query = query.filter(Connection.canvas_group == canvas_group)

            return [(c.canvas_group, c.te_group, c.te_type, c.delete_flag) for c in query]


class DeleteFlagAlreadySet(Exception):
    pass
