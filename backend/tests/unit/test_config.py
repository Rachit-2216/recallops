from recallops.config import Settings


def test_defaults_use_fake_memory_and_protect_reserve() -> None:
    settings = Settings(_env_file=None)
    assert settings.cognee_mode == "fake"
    assert settings.cognee_dataset == "recallops_evidence_v1"
    assert settings.cognee_token_supply == 14_000_000
    assert settings.cognee_protected_reserve == 6_000_000


def test_settings_repr_does_not_expose_api_key() -> None:
    settings = Settings(cognee_api_key="super-secret", _env_file=None)
    assert "super-secret" not in repr(settings)
