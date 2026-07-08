from __future__ import annotations

from typing import Any


class MarketDataService:
    """OHLCV·기술적 지표 데이터 (증권사 API / pykrx 연동 예정)."""

    def get_price_history(
        self,
        ticker: str,
        market: str = "KR",
        days: int = 90,
        limit: int | None = None,
    ) -> list[Any]:
        raise NotImplementedError("MarketDataService.get_price_history() 미구현")

    def get_technical_snapshot(
        self,
        ticker: str,
        market: str = "KR",
    ) -> dict[str, Any]:
        raise NotImplementedError("MarketDataService.get_technical_snapshot() 미구현")
