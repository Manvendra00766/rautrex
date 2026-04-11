"""Structured JSON logging configuration for Rautrex.

All log entries are emitted as JSON so they can be ingested by log
aggregation systems (Datadog, ELK, loki, etc.) without custom parsers.

Usage
-----
Called once at startup from main.py via setup_logging().
"""

import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as one-line JSON objects for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging() -> logging.Logger:
    """Configure root logger to output JSON to stdout.

    Returns the configured logger so callers can log via
    `logger = logging.getLogger("rautrex")`.
    """
    logger = logging.getLogger("rautrex")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Avoid double-logging if root logger already has handlers
    logging.getLogger("uvicorn.access").addHandler(handler)

    return logger
