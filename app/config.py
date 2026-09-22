"""Application configuration using Pydantic Settings"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Settings
    APP_NAME: str = "Chat Agent Queue System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000
    
    # Logging
    LOG_LEVEL: str = "DEBUG"
    
    # Supabase - All database operations
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # Use this for authenticated operations
    
    # Unipile API
    UNIPILE_API_DNS: str = "api16.unipile.com:14690"
    UNIPILE_API_KEY: str = ""
    
    # Scheduling Policy Defaults (set to 0 for instant testing)
    DEFAULT_MIN_DELAY_MINUTES: int = 0
    DEFAULT_MAX_DELAY_MINUTES: int = 0
    
    # Retry Settings
    MAX_RETRY_ATTEMPTS: int = 3
    
    # OpenAI API
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT") != "production" else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=False
    )


# Create global settings instance
settings = Settings()

