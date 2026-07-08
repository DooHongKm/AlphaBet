from __future__ import annotations

import asyncio
from typing import Sequence

from alphabet.agents.base import BaseAgent
from alphabet.agents.chart import ChartAgent
from alphabet.agents.financial import FinancialAgent
from alphabet.agents.macro import MacroAgent
from alphabet.agents.news import NewsAgent
from alphabet.agents.supervisor import SupervisorAgent
from alphabet.config import Settings, get_settings
from alphabet.schemas.common import AgentReport, AnalysisRequest, AnalysisResult
from alphabet.schemas.weights import AgentWeights


class AnalysisPipeline:
    """4개 전문 에이전트 병렬 실행 후 Supervisor가 통합한다."""

    def __init__(
        self,
        agents: Sequence[BaseAgent] | None = None,
        supervisor: SupervisorAgent | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.agents: list[BaseAgent] = list(agents or self._default_agents())
        self.supervisor = supervisor or SupervisorAgent()

    @staticmethod
    def _default_agents() -> list[BaseAgent]:
        return [
            FinancialAgent(),
            ChartAgent(),
            MacroAgent(),
            NewsAgent(use_hf=False),
        ]

    async def run(
        self,
        request: AnalysisRequest,
        weights: AgentWeights | None = None,
    ) -> AnalysisResult:
        reports = await self._run_agents_parallel(request)
        return self.supervisor.synthesize(request, reports, weights)

    async def _run_agents_parallel(
        self,
        request: AnalysisRequest,
    ) -> list[AgentReport]:
        tasks = [
            asyncio.wait_for(
                agent.analyze(request),
                timeout=self.settings.agent_timeout_sec,
            )
            for agent in self.agents
        ]
        return list(await asyncio.gather(*tasks))


async def run_analysis(
    ticker: str,
    question: str | None = None,
    market: str = "KR",
    use_hf_for_news: bool = False,
) -> AnalysisResult:
    """CLI·스크립트용 단축 진입점."""
    agents: list[BaseAgent] = [
        FinancialAgent(),
        ChartAgent(),
        MacroAgent(),
        NewsAgent(use_hf=use_hf_for_news),
    ]
    pipeline = AnalysisPipeline(agents=agents)
    request = AnalysisRequest(ticker=ticker, market=market, question=question)
    return await pipeline.run(request)
