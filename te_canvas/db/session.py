import os
import sys
import yaml
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from te_canvas.log import get_logger


logger = get_logger()


def get_sqlalchemy_conn_str(**kwargs) -> str:
    config = {}

    if 'CNAAS_DB_HOSTNAME' in os.environ:
        config['hostname'] = os.environ['CNAAS_DB_HOSTNAME']
    if 'CNAAS_DB_PORT' in os.environ:
        config['port'] = os.environ['CNAAS_DB_PORT']
    if 'CNAAS_DB_USERNAME' in os.environ:
        config['username'] = os.environ['CNAAS_DB_USERNAME']
    if 'CNAAS_DB_PASSWORD' in os.environ:
        config['password'] = os.environ['CNAAS_DB_PASSWORD']
    if 'CNAAS_CONFIGBASE' in os.environ:
        config['database'] = os.environ['CNAAS_CONFIGBSE']

    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as fd:
            try:
                config_yaml = yaml.safe_load(fd)
                config_yaml['hostname'] = config['database']['hostname']
                config_yaml['username'] = config['database']['username']
                config_yaml['password'] = config['database']['password']
                config_yaml['database'] = config['database']['database']
            except Exception as e:
                logger.debug(f'Failed to load configuration: {e}')
                sys.exit(-1)

    return (
        f"{config['type']}://{config['username']}:{config['password']}@"
        f"{config['hostname']}:{config['port']}/{config['database']}"
    )


conn_str = get_sqlalchemy_conn_str()
engine = create_engine(conn_str, pool_size=50, max_overflow=0)
Session = sessionmaker(bind=engine)


@contextmanager
def sqla_session(conn_str='', **kwargs):
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
