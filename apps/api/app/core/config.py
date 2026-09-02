from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _API_ROOT / ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/parent_health_agent"
    )
    cors_origins: str = "http://localhost:3000"
    whatsapp_invite_base_url: str = "http://localhost:3000/join"

    # Group creation depends on a separately hosted WhatsApp bridge. Keep it
    # explicitly opt-in so a slow or unavailable bridge can never delay signup.
    whatsapp_group_creation_enabled: bool = False
    whatsapp_bridge_base_url: str = ""
    whatsapp_group_name_template: str = "{parent_name}'s Care Circle"
    whatsapp_group_timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0)

    # Conservative SQLAlchemy pool settings for one small Render instance using
    # Supabase's connection pooler.
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=2, ge=0, le=20)
    database_pool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_pool_recycle_seconds: int = Field(default=300, ge=30, le=3600)

    @field_validator(
        "database_url",
        "cors_origins",
        "whatsapp_invite_base_url",
        "whatsapp_bridge_base_url",
        mode="before",
    )
    @classmethod
    def strip_string_settings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def normalized_invite_base_url(self) -> str:
        return self.whatsapp_invite_base_url.rstrip("/")

    @property
    def normalized_bridge_base_url(self) -> str:
        return self.whatsapp_bridge_base_url.rstrip("/")


settings = Settings()
