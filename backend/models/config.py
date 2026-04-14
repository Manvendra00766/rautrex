from backend.models.user import User
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


# Pydantic Settings reads from .env automatically via pydantic-settings.
# model_config with env_file tells Pydantic to load these env vars at
# instantiation time rather than relying on manual os.environ parsing.
# This keeps config access centralized and type-safe.


class Settings(BaseSettings):
    app_name: str = "Rautrex"
    debug: bool = False

    # Database — Supabase Postgres via asyncpg driver for async SQLAlchemy
    database_url: str = "postgresql+asyncpg://postgres:your-password@your-project-ref.supabase.co:5432/postgres"

    # JWT configuration
    secret_key: str = "change-me-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    frontend_url: str = "http://localhost:3000"
    
    # CORS origins (comma-separated, defaults to localhost)
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    resend_api_key: str = ""
    resend_from_email: str = "noreply@rautrex.dev"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_aliases(cls, value):
        if isinstance(value, str) and value.lower() == "release":
            return False
        return value

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # So DATABASE_URL and database_url both work
    )


settings = Settings()
