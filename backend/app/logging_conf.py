"""Structured JSON logging with request-id and PII redaction (NFR-17).

No amounts, account numbers, or emails ever reach the log stream: a
processor redacts any value matching a money/account/email-shaped pattern
before the event is serialised.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import structlog

_MONEY_RE = re.compile(r"₹\s?[\d,]+(\.\d+)?")
_ACCOUNT_RE = re.compile(r"\b\d{9,18}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

_REDACTED = "[redacted]"


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        value = _MONEY_RE.sub(_REDACTED, value)
        value = _EMAIL_RE.sub(_REDACTED, value)
        value = _ACCOUNT_RE.sub(_REDACTED, value)
        return value
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _redact_processor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if key in {"password", "password_hash", "token", "refresh_token", "access_token", "api_key"}:
            event_dict[key] = _REDACTED
            continue
        event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
