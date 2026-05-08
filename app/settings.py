from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    App settings loaded from environment variables.

    Required:
      - DATABASE_URL: SQLAlchemy async URL (e.g. postgresql+asyncpg://user:pass@host:5432/db)
      - SECRET_KEY: random secret for JWT signing (required in production)
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_debug: bool = False
    database_url: str
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    # Comma-separated list of allowed CORS origins, e.g. "https://example.com,https://www.example.com"
    cors_origins: str = "http://localhost:3000"
    # Draft classes from this year onwards have voting disabled (players haven't played a full season)
    voting_lock_from_year: int = 2026
    # Email / SMTP — leave smtp_host empty to disable email sending (dev mode)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"
    app_url: str = "http://localhost:3000"


settings = Settings()

if settings.app_env == "production" and settings.secret_key == "change-me-in-production":
    raise RuntimeError("SECRET_KEY environment variable must be set in production")
