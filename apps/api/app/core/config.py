from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/parent_health_agent"
    cors_origins: str = "http://localhost:3000"
    whatsapp_invite_base_url: str = "http://localhost:3000/join"
    whatsapp_bridge_base_url: str = "http://127.0.0.1:3000"
    whatsapp_group_name_template: str = "{parent_name}'s Care Circle"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
