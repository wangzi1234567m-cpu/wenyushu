from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    csrf_secret: SecretStr = Field(min_length=32)
    allowed_origins: list[str] = ["http://localhost:3000"]
    actor_ttl_seconds: int = Field(default=604800, gt=0)
    csrf_ttl_seconds: int = Field(default=3600, gt=0)
    max_body_bytes: int = Field(default=65536, ge=1, le=1048576)
    provider: Literal["mock"] = "mock"

    @model_validator(mode="after")
    def validate_settings(self):
        if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL psycopg URL required")
        if not self.allowed_origins or any(
            o.endswith("/") or "*" in o for o in self.allowed_origins
        ):
            raise ValueError("Exact origins without trailing slash required")
        if self.environment == "production":
            if any(not o.startswith("https://") for o in self.allowed_origins):
                raise ValueError("Production requires HTTPS origins")
            if "example" in self.csrf_secret.get_secret_value().lower():
                raise ValueError("Example secrets forbidden")
        return self
