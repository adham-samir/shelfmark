"""Structured request logging.

Every request produces exactly one line carrying its request ID, so a value a
client quotes from an error response can be traced to the call that produced it.
The ID used to be generated, returned, and then discarded.

Two formats share one logger:

* ``json`` (default) — one object per line, ready for a log shipper.
* ``text`` — ``SMART_ECOMMERCE_LOG_FORMAT=text`` for readable local debugging.

**What must never be logged:** ``Authorization`` and ``Cookie`` headers, request
or response bodies, email addresses, phone numbers, and delivery addresses. The
access line carries method, path, status, duration, and the request ID only.
Anything added here must keep that rule; a token in a log file is a leaked
credential, and the demonstration data contains real-looking contact details.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

LOGGER_NAME = "smart_ecommerce"
ACCESS_EVENT = "http_request"
ERROR_EVENT = "http_error"

#: The request ID of the request being served, if any.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

_RESERVED = frozenset(
    {
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
        "taskName",
        "message",
        "asctime",
    }
)

_configured = False


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the request ID and any extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _timestamp(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Readable single-line output for local runs."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        parts = [
            _timestamp(),
            record.levelname.ljust(7),
            getattr(record, "event", record.getMessage()),
        ]
        if request_id:
            parts.append(f"request_id={request_id}")
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in ("event", "request_id") and not key.startswith("_"):
                parts.append(f"{key}={value}")
        line = "  ".join(parts)
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def configure_logging() -> None:
    """Install the handler once. Safe to call from every lifespan.

    Called from the application lifespan rather than at import so that a bare
    ``TestClient`` — which does not run lifespan — leaves the stdlib defaults in
    place and keeps ``caplog`` working.
    """
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return

    level_name = os.getenv("SMART_ECOMMERCE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = os.getenv("SMART_ECOMMERCE_LOG_FORMAT", "json").strip().lower()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TextFormatter() if fmt == "text" else JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False

    # Our middleware emits the access line, so uvicorn's would be a duplicate.
    # uvicorn.error is left alone: startup and crash messages must still appear.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _configured = True


def access_logger() -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.access")


def error_logger() -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.error")
