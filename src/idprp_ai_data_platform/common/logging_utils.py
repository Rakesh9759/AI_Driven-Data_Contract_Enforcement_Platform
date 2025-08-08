"""Structured logging setup for platform services."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


_STANDARD_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


class _ContextFilter(logging.Filter):
    def __init__(self, app_name: str | None, environment: str | None) -> None:
        super().__init__()
        self._app_name = app_name
        self._environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        if self._app_name:
            setattr(record, "app_name", self._app_name)
        if self._environment:
            setattr(record, "environment", self._environment)
        return True


class JsonLogFormatter(logging.Formatter):
    """Formats logs as JSON to simplify downstream parsing."""

    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_")
        }
        if extras:
            event.update(extras)

        return json.dumps(event)


def setup_logging(level: str, app_name: str | None = None, environment: str | None = None) -> None:
    logger = logging.getLogger()
    logger.setLevel(level.upper())

    # Replace existing handlers so all modules emit a single structured stream.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonLogFormatter())
    stream_handler.addFilter(_ContextFilter(app_name=app_name, environment=environment))
    logger.addHandler(stream_handler)
