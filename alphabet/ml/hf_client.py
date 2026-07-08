from __future__ import annotations

from functools import lru_cache
from typing import Any

from alphabet.config import Settings, get_settings


class HFClient:
    """에이전트가 공유하는 HuggingFace 파이프라인 로더."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_pipeline(self, task: str, model: str, **kwargs: Any) -> Any:
        raise NotImplementedError("HFClient.get_pipeline() 미구현")


@lru_cache
def get_hf_client() -> HFClient:
    return HFClient()
