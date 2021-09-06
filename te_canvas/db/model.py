from sqlalchemy import Column, Integer, String

from te_canvas.db.session import Base, sqla_session


class Connection(Base):
    __tablename__ = 'connections'
    te_group = Column(String, primary_key=True)
    canvas_group = Column(String, primary_key=True)


class Event(Base):
    __tablename__ = 'events'
    te_id = Column(String, primary_key=True)
    canvas_id = Column(String, primary_key=True)
    te_group = Column(String)
    canvas_group = Column(String)


def add_connection(te_group, canvas_group):
    with sqla_session() as session:
        session.add(Connection(te_group=te_group, canvas_group=canvas_group))


def delete_connection(te_group, canvas_group):
    with sqla_session() as session:
        q = session.query(Connection).filter(
            Connection.te_group == te_group
            and Connection.canvas_group == canvas_group
        )
        if q.count() == 0:
            raise DeleteEmpty()
        q.delete()


def get_connections() -> [(str, str)]:
    with sqla_session() as session:
        # NOTE: We cannot return a list of Connection here, since the Session
        # they are connected to is closed at end of this block.
        return [(c.te_group, c.canvas_group) for c in session.query(Connection)]


class DeleteEmpty(Exception):
    pass
