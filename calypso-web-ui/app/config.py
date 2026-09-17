from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Calypso AI 中文安全运营控制台"
    version: str = "1.0.0"
    calypso_base_url: str = "https://us1.calypsoai.app"
    calypso_api_token: Optional[str] = None
    default_project_id: Optional[str] = None
    app_mode: str = "demo"  # "demo" 或 "online"
    port: int = 8080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
