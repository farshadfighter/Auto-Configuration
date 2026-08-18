from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NGFABRIC_", extra="ignore")

    app_name: str = "NGFabric"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://ngfabric:ngfabric@localhost:5432/ngfabric"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7

    # 32-byte base64 key for AES-256-GCM application-level secret encryption.
    # Generate with: python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"
    secret_encryption_key: str = ""

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
