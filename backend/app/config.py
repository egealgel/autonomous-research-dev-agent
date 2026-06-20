from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    database_url: str = "postgresql+psycopg://arda:arda_dev@localhost:5432/arda"
    redis_url: str = "redis://localhost:6379/0"
    storage_path: Path = Path("../storage")
    monthly_budget_usd: float = 20.0


settings = Settings()
