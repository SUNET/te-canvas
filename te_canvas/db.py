import logging
import os
import sys
from contextlib import contextmanager
from time import sleep
from typing import Optional

from psycopg2.errors import NoDataFound, UniqueViolation
from sqlalchemy import ARRAY, Boolean, Column, Integer, String, create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker  # type: ignore

from te_canvas.log import get_logger


def flat_list(query):
    """
    Utility method to get plain lists from SQLAlchemy's tuple lists.
    """
    return [r[0] for r in query]


Base = declarative_base()


class Connection(Base):
    """
    Connection stores TimeEdit objects "attached" to Canvas courses.

    In the UI one "block" corresponds to one connection.

    NOTE: For a given canvas_group C and te_group T, there can only be one connection. Once a
    connection's delete flag has been set the connection should not be modified, and a new
    connection (C, T) can not be added until the old one is deleted by sync.Syncer.
    """

    __tablename__ = "connections"
    canvas_group = Column(String, primary_key=True)
    te_group = Column(String, primary_key=True)
    te_type = Column(String)
    delete_flag = Column(Boolean, default=False)


class TemplateConfig(Base):
    __tablename__ = "template_config"
    id = Column(Integer, primary_key=True)
    config_type = Column(String)
    te_type = Column(String)
    te_field = Column(String)
    canvas_group = Column(String)


class WhitelistTypes(Base):
    __tablename__ = "whitelist_types"
    extid = Column(String, primary_key=True)


class SyncStatus(Base):
    __tablename__ = "sync_status"
    canvas_group = Column(String, primary_key=True)
    status = Column(String)


class Test(Base):
    """
    TODO: Can we avoid having this here and do this in test_db, perhaps dynamically in a test case?
    Not so important. But would be nice if this table is not included in the real database. In fact
    this table should not be necessary – since we use a separate test_db we can use any table for
    simple commit/rollback testing.
    """

    __tablename__ = "unittest"
    foo = Column(String, primary_key=True, default="bar")


class DB:
    """
    NOTE: The getters and setters in this class are used by the API but not Syncer. This is because
    Syncer needs closer control over sessions and error handling.
    """

    def __init__(self, **kwargs):
        """
        Open connection and initialize database.

        Database settings can come either from env vars or kwargs, where kwargs have precedence.
        """
        logger = get_logger()

        env_var_mapping = {
            "hostname": "POSTGRES_HOSTNAME",
            "port": "POSTGRES_PORT",
            "username": "POSTGRES_USER",
            "password": "POSTGRES_PASSWORD",
            "database": "POSTGRES_DB",
        }

        env_vars = {k: os.environ[v] for (k, v) in env_var_mapping.items() if v in os.environ}
        conn = env_vars | kwargs

        for k, v in env_var_mapping.items():
            if k not in conn:
                logger.critical(f"Missing env var: {v}")
                sys.exit(1)

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
                session.add(
                    Connection(
                        canvas_group=canvas_group,
                        te_group=te_group,
                        te_type=te_type,
                    )
                )
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

    def get_connections(self, canvas_group: Optional[str] = None) -> "list[tuple[str, str, str, bool]]":
        with self.sqla_session() as session:
            # NOTE: We cannot return a list of Connection here, since the Session they are connected
            # to is closed at end of this block.
            query = session.query(Connection)

            if canvas_group is not None:
                query = query.filter(Connection.canvas_group == canvas_group)

            return [(c.canvas_group, c.te_group, c.te_type, c.delete_flag) for c in query]

    def get_sync_status(self, canvas_group):
        with self.sqla_session() as session:
            query = session.query(SyncStatus).where(SyncStatus.canvas_group == canvas_group)
            if query.count() != 1:
                session.add(SyncStatus(canvas_group=canvas_group, status=""))
                return ""
            return query.one().status

    def update_sync_status(self, canvas_group, status: str):
        with self.sqla_session() as session:
            query = session.query(SyncStatus).filter(
                SyncStatus.canvas_group == canvas_group,
            )
            if query.count() != 1:
                session.add(SyncStatus(canvas_group=canvas_group, status=status))
                return
            query.one().status = status

    def get_whitelist_types(self):
        with self.sqla_session() as session:
            query = session.query(WhitelistTypes).all()
            return [wt.extid for wt in query]

    def add_whitelist_type(self, extid: str):
        with self.sqla_session() as session:
            duplicate_check = (
                session.execute(select(WhitelistTypes).where(WhitelistTypes.extid == extid)).first() is None
            )
            if duplicate_check:
                session.add(WhitelistTypes(extid=extid))
            else:
                raise UniqueViolation

    def delete_whitelist_type(self, extid: str):
        with self.sqla_session() as session:
            q = session.query(WhitelistTypes).filter(WhitelistTypes.extid == extid)
            if q.count() == 0:
                raise NoDataFound
            else:
                session.query(WhitelistTypes).filter(WhitelistTypes.extid == extid).delete()

    def get_template_config(self, canvas_group="") -> "list[tuple[int, str, str, str, str]]":
        with self.sqla_session() as session:
            if not canvas_group:
                query = session.query(TemplateConfig)
            else:
                query = session.query(TemplateConfig).where(TemplateConfig.canvas_group == canvas_group)
            return [
                (
                    r.id,
                    r.config_type,
                    r.te_type,
                    r.te_field,
                    r.canvas_group,
                )
                for r in query
            ]

    def delete_template_config(self, template_id: str):
        with self.sqla_session() as session:
            q = session.query(TemplateConfig).filter(TemplateConfig.id == int(template_id))
            if q.count() == 0:
                raise NoDataFound
            session.query(TemplateConfig).filter(TemplateConfig.id == template_id).delete()

    def add_template_config(self, config_type: str, te_type: str, te_field: str, canvas_group: Optional[str]):
        with self.sqla_session() as session:
            duplicate_check = (
                session.execute(
                    select(TemplateConfig)
                    .where(TemplateConfig.config_type == config_type)
                    .where(TemplateConfig.te_type == te_type)
                    .where(TemplateConfig.te_field == te_field)
                    .where(TemplateConfig.canvas_group == canvas_group)
                ).first()
                is None
            )
            te_type_count = len(
                session.execute(
                    select(TemplateConfig)
                    .where(TemplateConfig.config_type == config_type)
                    .where(TemplateConfig.canvas_group == canvas_group)
                ).all()
            )
            if duplicate_check is True and te_type_count < 3:
                session.add(
                    TemplateConfig(
                        config_type=config_type,
                        te_type=te_type,
                        te_field=te_field,
                        canvas_group=canvas_group,
                    )
                )
            else:
                raise UniqueViolation


class DeleteFlagAlreadySet(Exception):
    pass
