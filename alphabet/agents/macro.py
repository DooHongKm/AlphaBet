from __future__ import annotations

from alphabet.agents.base import BaseAgent
from alphabet.schemas.common import (
    AgentName,
    AgentReport,
    AnalysisRequest,
    Signal,
)
from alphabet.services.macro_data import MacroDataService


class MacroAgent(BaseAgent):
    """거시경제 환경 분석 에이전트."""

    name = AgentName.MACRO

    def __init__(self, data_service: MacroDataService | None = None) -> None:
        self.data_service = data_service or MacroDataService()

    def default_question(self, request: AnalysisRequest) -> str:
        return "현재 거시경제 환경이 주식에 유리한가?"

    async def analyze(self, request: AnalysisRequest) -> AgentReport:
        # TODO: data_service 연동 및 거시 지표 평가 로직 구현
        return AgentReport(
            agent=self.name,
            signal=Signal.NEUTRAL,
            confidence=0.0,
            horizon=request.horizon,
            summary="[미구현] 거시경제 분석",
            key_points=[],
            evidence=[],
            risks=[],
        )
