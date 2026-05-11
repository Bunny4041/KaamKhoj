from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, EmailStr
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "KaamKhoj"
    APP_ENV: str = "development"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/kaamkhoj"
    SYNC_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/kaamkhoj"

    # Auth
    SECRET_KEY: str = "change-me-in-production-must-be-at-least-32-characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_NAME: str = "KaamKhoj"
    EMAILS_FROM_EMAIL: str = "noreply@kaamkhoj.in"
    EMAILS_ENABLED: bool = False

    # Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
