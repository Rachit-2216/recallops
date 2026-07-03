from recallops.logging import redact_event

KEY_PREFIX = "cognee_key_"


def test_redacts_sensitive_keys_recursively() -> None:
    event = {
        "authorization": "Bearer secret-token",
        "nested": {
            "x-api-key": "provider-secret",
            "COGNEE_API_KEY": KEY_PREFIX + "abcdefghijklmnopqrstuvwxyz",
        },
        "request_id": "safe-request-id",
    }

    redacted = redact_event(event)

    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["x-api-key"] == "[REDACTED]"
    assert redacted["nested"]["COGNEE_API_KEY"] == "[REDACTED]"
    assert redacted["request_id"] == "safe-request-id"


def test_redacts_cognee_key_patterns_inside_safe_fields() -> None:
    event = {
        "safe_error": (f"provider rejected {KEY_PREFIX}abcdefghijklmnopqrstuvwxyz during setup"),
    }

    redacted = redact_event(event)

    assert redacted["safe_error"] == "provider rejected [REDACTED] during setup"
