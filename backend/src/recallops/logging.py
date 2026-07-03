import re
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

SENSITIVE_KEYS = {
    "authorization",
    "cognee_api_key",
    "demo_admin_token",
    "x-api-key",
}
COGNEE_KEY_PATTERN = re.compile(
    r"\bcognee_(?:key|sk)_[A-Za-z0-9_-]{12,}\b",
    re.IGNORECASE,
)
REDACTED = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return COGNEE_KEY_PATTERN.sub(REDACTED, value)
    if isinstance(value, Mapping):
        return redact_event(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def redact_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: (REDACTED if key.casefold() in SENSITIVE_KEYS else _redact_value(value))
        for key, value in event.items()
    }


def _redaction_processor(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    return redact_event(event_dict)


def configure_logging() -> None:
    structlog.configure(
        processors=[
            _redaction_processor,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> Any:
    return structlog.get_logger("recallops")
