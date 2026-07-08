from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # HuggingFace
    hf_token: str | None = None
    hf_device: str = "auto"
    hf_cache_dir: Path | None = None
    hf_sentiment_model: str = "ProsusAI/finbert"
    hf_summarization_model: str = "facebook/bart-large-cnn"

    # 외부 API (추후 연동)
    dart_api_key: str | None = None
    news_api_key: str | None = None

    # 한국투자증권 Open API
    kis_app_key: str | None = None
    kis_app_secret: str | None = None
    kis_is_mock: bool = False

    # 오케스트레이션
    agent_timeout_sec: float = 120.0
    max_parallel_agents: int = 4

    # 데이터 저장 (추후 구현)
    db_path: Path = Path("data/alphabet.db")
    cache_ttl_sec: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
