import logging
import os
import sys
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from te_canvas.log import get_logger

logger = get_logger()

try:
    hostname = os.environ["TE_CANVAS_DB_HOSTNAME"]
    port = os.environ["TE_CANVAS_DB_PORT"]
    username = os.environ["TE_CANVAS_DB_USERNAME"]
    password = os.environ["TE_CANVAS_DB_PASSWORD"]
    database = os.environ["TE_CANVAS_DB_DATABASE"]
except Exception as e:
    logger.debug(f"Failed to load configuration: {e}")
    sys.exit(-1)

conn_str = f"postgresql+psycopg2://{username}:{password}@{hostname}:{port}/{database}"

Base = declarative_base()
engine = create_engine(conn_str, pool_size=50, max_overflow=0)
Session = sessionmaker(bind=engine)

# TODO: Is this correct?
logging.getLogger("sqlalchemy.engine").addHandler(logger.handlers[0])
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


@contextmanager
def sqla_session(conn_str="", **kwargs):
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
