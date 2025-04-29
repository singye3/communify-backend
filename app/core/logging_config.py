# app/core/logging_config.py
import logging
import sys
import os
from logging.config import dictConfig

from app.core.config import settings # To potentially get log level from settings

# Define Log Levels mapping (optional, but can be useful)
LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

# Get desired log level from environment or default to INFO
log_level_str = os.getenv("LOG_LEVEL", "INFO").lower()
numeric_log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

LOG_FORMAT = "%(levelname)-8s | %(asctime)s | %(name)-25s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Logging configuration dictionary
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
        "app": {"handlers": ["default"], "level": numeric_log_level, "propagate": False},

        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False}, # Uvicorn's own logs
        "uvicorn.error": {"level": "INFO", "handlers": ["default"], "propagate": False}, # Uvicorn errors
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False}, # Uvicorn access logs
    },
}

def setup_logging():
    """Applies the logging configuration."""
    print(f"Setting up logging with level: {logging.getLevelName(numeric_log_level)} ({numeric_log_level})")
    dictConfig(logging_config)
    logger = logging.getLogger("app.core.logging_config")
    logger.info("Logging setup complete.")

def get_logger(name: str) -> logging.Logger:
    """Gets a logger instance with the specified name."""
    return logging.getLogger(f"app.{name}") 