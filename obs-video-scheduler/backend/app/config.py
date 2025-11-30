from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data.db"
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str | None = None
    server_video_dir: Path = Path("./media")
    obs_video_dir: Path = Path("./media")

    model_config = SettingsConfigDict(env_prefix="OBS_SCHEDULER_", env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
