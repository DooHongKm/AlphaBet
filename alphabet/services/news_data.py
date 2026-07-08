from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsItem:
    title: str
    summary: str
    published_at: datetime
    source: str
    url: str | None = None


class NewsDataService:
    """뉴스·공시 수집 (NewsAPI / DART 공시 / RSS 연동 예정)."""

    def get_recent_news(
        self,
        ticker: str,
        market: str = "KR",
        limit: int = 10,
    ) -> list[NewsItem]:
        raise NotImplementedError("NewsDataService.get_recent_news() 미구현")
