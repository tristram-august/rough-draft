from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    App settings loaded from environment variables.

    Required:
      - DATABASE_URL: SQLAlchemy async URL (e.g. postgresql+asyncpg://user:pass@host:5432/db)
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_debug: bool = False
    database_url: str


settings = Settings()
