from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
        populate_by_name=True,
    )

    env: Literal["local", "test", "production"] = "local"
    database_url: str = "sqlite+aiosqlite:///./recallops.db"
    public_origin: str = "http://localhost:5173"
    demo_mode: bool = True
    demo_bootstrap: bool = False
    e2e_mode: bool = False
    allow_url_ingestion: bool = False
    demo_admin_token: SecretStr = SecretStr("change-this-local-token")
    cognee_mode: Literal["fake", "live"] = "fake"
    cognee_dataset: str = "recallops_evidence_v1"
    cognee_token_supply: int = 14_000_000
    cognee_protected_reserve: int = 6_000_000
    cognee_base_url: str | None = Field(
        default=None,
        validation_alias="COGNEE_BASE_URL",
    )
    cognee_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="COGNEE_API_KEY",
    )

    @model_validator(mode="after")
    def validate_budget(self) -> Self:
        if self.cognee_protected_reserve >= self.cognee_token_supply:
            raise ValueError("protected reserve must be smaller than token supply")
        if self.cognee_mode == "live" and (
            not self.cognee_base_url
            or self.cognee_api_key is None
            or not self.cognee_api_key.get_secret_value()
        ):
            raise ValueError("live Cognee mode requires base URL and API key")
        return self
