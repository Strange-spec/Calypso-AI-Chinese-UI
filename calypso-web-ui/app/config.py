from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Calypso AI 中文安全运营控制台"
    version: str = "1.0.0"
    calypso_base_url: str = "https://us1.calypsoai.app"
    calypso_api_token: Optional[str] = "MDFhMGFmYjQtNGFiYS03MDc4LTk3Y2MtMzVhMmZhNjQzZjQ3/hXLIByTz8rsvxaI4fz2v47kQBOffVrqVRyovLSuk8ZrBedKu3QEKPhDlaU29VInDJxdiGllKYlJPr24HNgB4w"
    default_project_id: Optional[str] = None
    app_mode: str = "online"  # "demo" 或 "online"
    port: int = 8080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def get_effective_token(request=None) -> Optional[str]:
    """从 HTTP Authorization 请求头优先提取 Token，缺省则回退至全局配置。"""
    if request is not None and hasattr(request, "headers"):
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            val = auth[7:].strip()
            if val:
                return val
    return settings.calypso_api_token
