"""Central application configuration, loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "FinMate"
    APP_TAGLINE: str = "Your Money. Smarter."
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./data/finmate.db"

    # AWS RDS IAM database authentication. When enabled, the app never stores a DB password --
    # it asks AWS for a short-lived (~15 min) auth token per new connection instead. Uses
    # boto3's standard credential chain (env vars, ~/.aws/credentials, or an EC2/ECS role) --
    # no AWS key is ever put in this file.
    RDS_IAM_AUTH: bool = False
    RDS_HOST: str = ""
    RDS_PORT: int = 5432
    RDS_DB_NAME: str = "postgres"
    RDS_USER: str = "postgres"
    AWS_REGION: str = "ap-south-1"

    SECRET_KEY: str = "dev-secret-change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = "HS256"

    AI_PROVIDER: str = "mock"  # none | mock | openai | anthropic | gemini | local
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_BASE_URL: str = ""  # for local providers

    MAX_UPLOAD_SIZE_MB: int = 25
    UPLOAD_DIR: str = "./uploads"
    REPORTS_DIR: str = "./reports"

    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
