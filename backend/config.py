"""Application configuration and settings."""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str:
    """Locate the most appropriate .env file (repo root fallback -> backend/.env)."""
    backend_dir = Path(__file__).resolve().parent
    repo_root = backend_dir.parent
    
    candidates = [
        repo_root / ".env",      # preferred: root-level .env (earlier behavior)
        backend_dir / ".env",    # fallback: backend/.env (current file)
    ]
    
    chosen: Optional[Path] = next((path for path in candidates if path.exists()), None)
    return str(chosen or backend_dir / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # SinkIn API (pydantic will match SINKIN_API_KEY in .env automatically)
    sinkin_api_key: str = ""
    sinkin_base_url: str = "https://sinkin.ai/api"
    
    # Storage paths
    images_dir: str = str(Path(__file__).resolve().parent / "storage" / "images")
    assets_dir: str = str(Path(__file__).resolve().parent / "storage" / "assets")
    
    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,  # Allows matching SINKIN_API_KEY to sinkin_api_key
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    print(f"DEBUG: Loaded settings. API Key present: {bool(settings.sinkin_api_key)}")
    return settings
