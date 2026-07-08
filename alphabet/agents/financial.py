from __future__ import annotations

from alphabet.agents.base import BaseAgent
from alphabet.schemas.common import (
    AgentName,
    AgentReport,
    AnalysisRequest,
    Signal,
)
from alphabet.services.financial_data import FinancialDataService


class FinancialAgent(BaseAgent):
    """재무제표·밸류에이션 기반 분석 에이전트."""

    name = AgentName.FINANCIAL

    def __init__(self, data_service: FinancialDataService | None = None) -> None:
        self.data_service = data_service or FinancialDataService()

    def default_question(self, request: AnalysisRequest) -> str:
        return f"{request.ticker}는 돈을 잘 버는 회사인가?"

    async def analyze(self, request: AnalysisRequest) -> AgentReport:
        # TODO: data_service 연동 및 재무 지표 평가 로직 구현
        return AgentReport(
            agent=self.name,
            signal=Signal.NEUTRAL,
            confidence=0.0,
            horizon=request.horizon,
            summary=f"[미구현] {request.ticker} 재무 분석",
            key_points=[],
            evidence=[],
            risks=[],
        )
