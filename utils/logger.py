"""
Structured logging for Video Viral Analyzer.
Uses Rich for beautiful console output.
"""

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

console = Console()

_loggers: dict = {}

LOG_DIR = "logs"
LOG_FILE = "go-viral-video.log"
JSON_LOG_FILE = "go-viral-video.json.log"


class JSONFormatter(logging.Formatter):
    """Format log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def configure_logging():
    """
    Configure global logging settings.
    Call once at application startup.
    Adds file and JSON handlers when LOG_TO_FILE=1 env var is set.
    Clears cached loggers to avoid duplicate handlers.
    """
    global _loggers

    _loggers.clear()

    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    if os.environ.get("LOG_TO_FILE") == "1":
        os.makedirs(LOG_DIR, exist_ok=True)

        log_path = os.path.join(LOG_DIR, LOG_FILE)
        json_log_path = os.path.join(LOG_DIR, JSON_LOG_FILE)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(name)s %(message)s")
        )
        file_handler.setLevel(level)

        json_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(level)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(json_handler)


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Create or retrieve a named logger with Rich formatting.

    Args:
        name: Logger name (typically module name).
        level: Logging level. Defaults to INFO.

    Returns:
        Configured logger instance.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level or logging.INFO)

    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger


def set_global_level(level: int):
    """Set logging level for all loggers."""
    for logger in _loggers.values():
        logger.setLevel(level)
