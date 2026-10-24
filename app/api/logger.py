import os
import logging
from logging.config import dictConfig
from .config import get_settings
from dotenv import load_dotenv

load_dotenv()
class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def setup_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "default": {
                "format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            },
            "color": {
                "()": ColorFormatter,
                "format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "color",
                "level": "DEBUG",
            },

        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },

        "loggers": {
            "uvicorn": {"handlers": ["console"], "level": "INFO"},
            "uvicorn.error": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "uvicorn.access": {"handlers": ["console"], "level": "INFO"},
        },
    })
