"""Application configuration and settings."""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # SinkIn API (pydantic will match SINKIN_API_KEY in .env automatically)
    sinkin_api_key: str = ""
    sinkin_base_url: str = "https://sinkin.ai/api"
    
    # Storage paths
    images_dir: str = "storage/images"
    assets_dir: str = "storage/assets"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False  # This allows matching SINKIN_API_KEY to sinkin_api_key
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    print(f"DEBUG: Loaded settings. API Key present: {bool(settings.sinkin_api_key)}")
    return settings
