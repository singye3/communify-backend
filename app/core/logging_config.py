import logging
import sys
import os
from logging.config import dictConfig

from app.core.config import settings

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

log_level_str = os.getenv("LOG_LEVEL", "INFO").lower()
numeric_log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

LOG_FORMAT = "%(levelname)-8s | %(asctime)s | %(name)-25s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": DATE_FORMAT,
            "use_colors": True,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelname)-8s | %(asctime)s | %(client_addr)s | "%(request_line)s" %(status_code)s',
            "datefmt": DATE_FORMAT,
            "use_colors": True,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["default"],
            "level": numeric_log_level,
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


def setup_logging():
    print(
        f"Setting up logging with level: {logging.getLevelName(numeric_log_level)} ({numeric_log_level})"
    )
    dictConfig(logging_config)
    logger = logging.getLogger("app.core.logging_config")
    logger.info("Logging setup complete.")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"app.{name}")
