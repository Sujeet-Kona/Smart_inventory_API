from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    # App info
    app_name: str = "SmartInventory API"
    app_version: str = "1.0.0"
    debug: bool = False

    # JWT authentication
    jwt_secret_key: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30


@lru_cache()
def get_settings() -> Settings:
    """
    Load settings once at startup and cache them.
    lru_cache ensures we don't re-read the .env file on every request.
    """
    return Settings()
