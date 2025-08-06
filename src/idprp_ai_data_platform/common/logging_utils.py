"""Structured logging setup for platform services."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonLogFormatter(logging.Formatter):
    """Formats logs as JSON to simplify downstream parsing."""

    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(event)


def setup_logging(level: str) -> None:
    logger = logging.getLogger()
    logger.setLevel(level.upper())

    # Replace existing handlers so all modules emit a single structured stream.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonLogFormatter())
    logger.addHandler(stream_handler)
