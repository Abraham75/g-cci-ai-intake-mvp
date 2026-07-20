from __future__ import annotations
import os


class Settings:
    PROJECT_NAME = os.getenv("PROJECT_NAME", "G-CCI AI Intake MVP")
    VERSION = os.getenv("VERSION", "1.1.0-demo")
    API_V1_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/gcci")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-before-production")


settings = Settings()
