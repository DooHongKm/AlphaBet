from __future__ import annotations

from typing import TYPE_CHECKING

from alphabet.agents.base import BaseAgent
from alphabet.schemas.common import (
    AgentName,
    AgentReport,
    AnalysisRequest,
    Signal,
)
from alphabet.services.news_data import NewsDataService

if TYPE_CHECKING:
    from alphabet.ml.sentiment import SentimentAnalyzer


class NewsAgent(BaseAgent):
    """뉴스·공시 수집 및 감성 분석 에이전트."""

    name = AgentName.NEWS

    def __init__(
        self,
        data_service: NewsDataService | None = None,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        use_hf: bool = False,
    ) -> None:
        self.data_service = data_service or NewsDataService()
        self.sentiment_analyzer = sentiment_analyzer
        self.use_hf = use_hf

    def default_question(self, request: AnalysisRequest) -> str:
        return f"{request.ticker}에 최근 호재·악재가 있는가?"

    async def analyze(self, request: AnalysisRequest) -> AgentReport:
        # TODO: data_service 연동 및 HF 감성 분석 로직 구현
        return AgentReport(
            agent=self.name,
            signal=Signal.NEUTRAL,
            confidence=0.0,
            horizon=request.horizon,
            summary=f"[미구현] {request.ticker} 뉴스/감성 분석",
            key_points=[],
            evidence=[],
            risks=[],
        )
