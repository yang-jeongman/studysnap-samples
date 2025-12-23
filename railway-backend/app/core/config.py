"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # App Info
    APP_NAME: str = "StudySnap API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API Keys
    ANTHROPIC_API_KEY: str

    # Database
    DATABASE_URL: str

    # GitHub
    GITHUB_TOKEN: str
    GITHUB_REPO_OWNER: str = "yang-jeongman"
    GITHUB_REPO_NAME: str = "StudySnap-Backend"
    GITHUB_OUTPUT_PATH: str = "outputs"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str = "support@studysnap.kr"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: str = "https://studysnap-pdf.netlify.app"

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Server
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Railway
    RAILWAY_ENVIRONMENT: str = "development"

    # Template System
    TEMPLATE_BASE_PATH: str = "sample_templates"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
