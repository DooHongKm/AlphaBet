from __future__ import annotations

from abc import ABC, abstractmethod

from alphabet.schemas.common import AgentName, AgentReport, AnalysisRequest


class BaseAgent(ABC):
    name: AgentName

    @abstractmethod
    async def analyze(self, request: AnalysisRequest) -> AgentReport:
        """종목 분석을 수행하고 정규화된 리포트를 반환한다."""

    def build_question(self, request: AnalysisRequest) -> str:
        if request.question:
            return request.question
        return self.default_question(request)

    @abstractmethod
    def default_question(self, request: AnalysisRequest) -> str:
        """에이전트별 기본 질문."""
