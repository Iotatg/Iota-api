"""Structured JSON logging with secret redaction.

All log records are emitted as single-line JSON. A small set of keys are
auto-redacted so that secrets never appear in logs, even by accident.
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any, Mapping

from pythonjsonlogger import jsonlogger

# Keys whose values are ALWAYS redacted, regardless of log message text.
REDACT_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "s3_access_key",
    "s3_secret_key",
    "admin_token",
    "cookie",
    "set-cookie",
}

# Patterns to scrub out of free-form log messages.
REDACT_PATTERNS = [
    re.compile(r"iota_[a-f0-9]{32,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"key=[A-Za-z0-9_\-]{16,}"),
    re.compile(r"password=[^\s&]+", re.IGNORECASE),
]

_REDACTED = "***REDACTED***"


def _redact_value(v: Any) -> Any:
    if isinstance(v, str):
        return _redact(v)
    return _REDACTED


def _redact(text: str) -> str:
    out = text
    for p in REDACT_PATTERNS:
        out = p.sub(_REDACTED, out)
    return out


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Apply to the formatted message and any string fields
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, Mapping):
                record.args = {
                    k: (_REDACTED if k.lower() in REDACT_KEYS else _redact(str(v)))
                    if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _redact(a) if isinstance(a, str) else a for a in record.args
                )
        return True


class _RedactingJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        # Add standard fields
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        # Redact known secret keys
        for k in list(log_record.keys()):
            if k.lower() in REDACT_KEYS:
                log_record[k] = _REDACTED
        # Redact any string field values
        for k, v in list(log_record.items()):
            if isinstance(v, str):
                log_record[k] = _redact(v)


def configure_logging(level: str = "info") -> None:
    """Configure root logger to emit structured JSON to stdout."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove any existing handlers (e.g. uvicorn's default)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    formatter = _RedactingJsonFormatter(
        "%(asctime)s %(level)s %(name)s %(message)s",
        rename_fields={"asctime": "ts", "name": "logger"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(_RedactingFilter())
    root.addHandler(handler)

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
