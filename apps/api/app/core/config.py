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

    # Hosted Meta WhatsApp Cloud API integration. Disabled until a real
    # WhatsApp Business number, permanent access token, app secret, webhook
    # verify token, and phone-number ID are configured in the hosted backend.
    whatsapp_cloud_enabled: bool = False
    whatsapp_cloud_verify_token: str = ""
    whatsapp_cloud_app_secret: str = ""
    whatsapp_cloud_access_token: str = ""
    whatsapp_cloud_phone_number_id: str = ""
    whatsapp_cloud_graph_version: str = Field(
        default="v25.0",
        pattern=r"^v\d+\.\d+$",
    )
    whatsapp_cloud_landing_url: str = "https://parent-health-agent.vercel.app"
    whatsapp_cloud_timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0)
    whatsapp_cloud_max_webhook_bytes: int = Field(
        default=262_144,
        ge=16_384,
        le=1_048_576,
    )
    whatsapp_cloud_auto_start_enabled: bool = False
    whatsapp_cloud_onboarding_template_name: str = ""
    whatsapp_cloud_onboarding_template_language: str = "en_US"

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
        "whatsapp_cloud_verify_token",
        "whatsapp_cloud_app_secret",
        "whatsapp_cloud_access_token",
        "whatsapp_cloud_phone_number_id",
        "whatsapp_cloud_graph_version",
        "whatsapp_cloud_landing_url",
        "whatsapp_cloud_onboarding_template_name",
        "whatsapp_cloud_onboarding_template_language",
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

    @property
    def normalized_cloud_landing_url(self) -> str:
        return self.whatsapp_cloud_landing_url.rstrip("/")

    @property
    def whatsapp_cloud_ready(self) -> bool:
        return self.whatsapp_cloud_enabled and all(
            (
                self.whatsapp_cloud_verify_token,
                self.whatsapp_cloud_app_secret,
                self.whatsapp_cloud_access_token,
                self.whatsapp_cloud_phone_number_id,
                self.whatsapp_cloud_graph_version,
            )
        )

    @property
    def whatsapp_cloud_auto_start_ready(self) -> bool:
        return (
            self.whatsapp_cloud_ready
            and self.whatsapp_cloud_auto_start_enabled
            and bool(self.whatsapp_cloud_onboarding_template_name)
            and bool(self.whatsapp_cloud_onboarding_template_language)
        )


settings = Settings()
