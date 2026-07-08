from __future__ import annotations

from typing import Any


class FinancialDataService:
    """재무제표·밸류에이션 데이터 (DART / SEC / yfinance 연동 예정)."""

    def get_financial_summary(
        self,
        ticker: str,
        market: str = "KR",
    ) -> dict[str, Any]:
        raise NotImplementedError("FinancialDataService.get_financial_summary() 미구현")
