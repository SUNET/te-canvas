from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects import postgresql

from te_canvas.db.session import Base, sqla_session, engine

#
# Data model
#
# Connections from TimeEdit to Canvas are many-to-one. A Canvas group have at
# most one connection. So `canvas_group` is a unique identifier for connections.
#


class Connection(Base):
    __tablename__ = "connections"
    canvas_group = Column(String, primary_key=True)
    te_groups = Column(postgresql.ARRAY(String))
    delete_flag = Column(Boolean, default=False)


class Event(Base):
    __tablename__ = "events"
    te_id = Column(String, primary_key=True)
    canvas_id = Column(String, primary_key=True)
    canvas_group = Column(String)


def add_connection(canvas_group: str, te_groups: [str]):
    with sqla_session() as session:
        session.add(Connection(canvas_group=canvas_group, te_groups=te_groups))


def delete_connection(canvas_group: str):
    with sqla_session() as session:
        session.query(Connection).filter(
            Connection.canvas_group == canvas_group
        ).one().delete_flag = True


def get_connections() -> [(str, [str], bool)]:
    with sqla_session() as session:
        # NOTE: We cannot return a list of Connection here, since the Session
        # they are connected to is closed at end of this block.
        return [
            (c.canvas_group, c.te_groups, c.delete_flag)
            for c in session.query(Connection)
        ]


Base.metadata.create_all(engine)
