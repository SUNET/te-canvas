import logging
import os
import sys
from contextlib import contextmanager

from sqlalchemy import Boolean, Column, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from te_canvas.log import get_logger

Base = declarative_base()


class Connection(Base):
    __tablename__ = "connections"
    canvas_group = Column(String, primary_key=True)
    te_group = Column(String, primary_key=True)
    delete_flag = Column(Boolean, default=False)


class Event(Base):
    __tablename__ = "events"
    canvas_id = Column(String, primary_key=True)
    te_id = Column(String, primary_key=True)
    canvas_group = Column(String)
    te_group = Column(String)


class DB:
    def __init__(self, **kwargs):
        logger = get_logger()

        env_var_mapping = {
            "hostname": "TE_CANVAS_DB_HOSTNAME",
            "port": "TE_CANVAS_DB_PORT",
            "username": "TE_CANVAS_DB_USERNAME",
            "password": "TE_CANVAS_DB_PASSWORD",
            "database": "TE_CANVAS_DB_DATABASE",
        }

        env_vars = {
            k: os.environ[v] for (k, v) in env_var_mapping.items() if v in os.environ
        }
        conn = kwargs | env_vars

        try:
            conn_str = "postgresql+psycopg2://{}:{}@{}:{}/{}".format(
                conn["username"],
                conn["password"],
                conn["hostname"],
                conn["port"],
                conn["database"],
            )
        except Exception as e:
            logger.debug(f"Failed to load configuration: {e}")
            sys.exit(-1)

        engine = create_engine(conn_str, pool_size=50, max_overflow=0)
        self.Session = sessionmaker(bind=engine)

        logging.getLogger("sqlalchemy.engine").addHandler(logger.handlers[0])
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

        Base.metadata.create_all(engine)

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

    def add_connection(self, canvas_group: str, te_group: str):
        with self.sqla_session() as session:
            session.add(Connection(canvas_group=canvas_group, te_group=te_group))

    def delete_connection(self, canvas_group: str, te_group: str):
        with self.sqla_session() as session:
            session.query(Connection).filter(
                Connection.te_group == te_group
                and Connection.canvas_group == canvas_group
            ).one().delete_flag = True

    def get_connections(self) -> list[tuple[str, str, bool]]:
        with self.sqla_session() as session:
            # NOTE: We cannot return a list of Connection here, since the Session
            # they are connected to is closed at end of this block.
            return [
                (c.canvas_group, c.te_group, c.delete_flag)
                for c in session.query(Connection)
            ]
