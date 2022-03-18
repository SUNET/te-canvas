import logging

from flask import current_app


# (?): Uses Flask logger if available?
def get_logger():
    if current_app:
        logger = current_app.logger
    else:
        logger = logging.getLogger("te-canvas")
        if not logger.handlers:
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
