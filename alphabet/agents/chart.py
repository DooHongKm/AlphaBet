from __future__ import annotations

from alphabet.agents.base import BaseAgent
from alphabet.schemas.common import (
    AgentName,
    AgentReport,
    AnalysisRequest,
    Signal,
)
from alphabet.services.market_data import MarketDataService


class ChartAgent(BaseAgent):
    """차트·기술적 지표 기반 분석 에이전트."""

    name = AgentName.CHART

    def __init__(self, data_service: MarketDataService | None = None) -> None:
        self.data_service = data_service or MarketDataService()

    def default_question(self, request: AnalysisRequest) -> str:
        return f"{request.ticker} 차트·패턴 기반 주가 전망은?"

    async def analyze(self, request: AnalysisRequest) -> AgentReport:
        # TODO: data_service 연동 및 차트 예측 로직 구현
        return AgentReport(
            agent=self.name,
            signal=Signal.NEUTRAL,
            confidence=0.0,
            horizon=request.horizon,
            summary=f"[미구현] {request.ticker} 차트 분석",
            key_points=[],
            evidence=[],
            risks=[],
        )
