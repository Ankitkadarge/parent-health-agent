from pydantic_settings import BaseSettings, SettingsConfigDict


class WhatsappMetaMisconfiguredError(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/parent_health_agent"
    cors_origins: str = "http://localhost:3000"
    whatsapp_invite_base_url: str = "http://localhost:3000/join"
    whatsapp_bridge_base_url: str = "http://127.0.0.1:3000"
    whatsapp_group_name_template: str = "{parent_name}'s Care Circle"
    whatsapp_signup_url: str = "http://localhost:3000"

    # Hosted (Meta WhatsApp Cloud API) onboarding. Provider is "none" by
    # default so local/test environments never need any of this configured.
    # Everything below stays optional at the settings level — validity is
    # enforced by `assert_whatsapp_meta_configured()`, called only from the
    # webhook routes, so importing this module never fails in an environment
    # that isn't running hosted WhatsApp.
    whatsapp_provider: str = "none"
    whatsapp_meta_phone_number_id: str | None = None
    whatsapp_meta_access_token: str | None = None
    whatsapp_meta_app_secret: str | None = None
    whatsapp_webhook_verify_token: str | None = None
    whatsapp_meta_graph_api_version: str = "v21.0"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def whatsapp_meta_enabled(self) -> bool:
        return self.whatsapp_provider.strip().lower() == "meta"

    def assert_whatsapp_meta_configured(self) -> None:
        """Fail safely (clear error, no crash at import time) when Meta mode
        is turned on but a required value is missing. Never called unless
        whatsapp_provider=meta, so this has zero effect on local/test setups.
        """
        if not self.whatsapp_meta_enabled:
            return
        required = {
            "WHATSAPP_META_PHONE_NUMBER_ID": self.whatsapp_meta_phone_number_id,
            "WHATSAPP_META_ACCESS_TOKEN": self.whatsapp_meta_access_token,
            "WHATSAPP_META_APP_SECRET": self.whatsapp_meta_app_secret,
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN": self.whatsapp_webhook_verify_token,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise WhatsappMetaMisconfiguredError(
                "WHATSAPP_PROVIDER=meta requires: " + ", ".join(sorted(missing))
            )


settings = Settings()
