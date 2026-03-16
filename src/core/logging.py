# import logging
# import sys
# from src.core.config import settings


# def setup_logging() -> None:
#     level = logging.DEBUG if settings.DEBUG else logging.INFO
#     logging.basicConfig(
#         level=level,
#         format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S",
#         handlers=[logging.StreamHandler(sys.stdout)],
#     )
#     logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
#     logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# def get_logger(name: str) -> logging.Logger:
#     return logging.getLogger(name)

import logging
import sys


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


temple_logger  = get_logger("temple")
darshan_logger = get_logger("darshan")