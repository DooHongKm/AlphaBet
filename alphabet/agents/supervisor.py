from __future__ import annotations

from alphabet.agents.base import BaseAgent
from alphabet.schemas.common import (
    AgentName,
    AgentReport,
    AnalysisRequest,
    AnalysisResult,
    Signal,
)
from alphabet.schemas.weights import AgentWeights, default_weights_for_horizon

SIGNAL_SCORE = {
    Signal.BULLISH: 1.0,
    Signal.NEUTRAL: 0.0,
    Signal.BEARISH: -1.0,
}


class SupervisorAgent(BaseAgent):
    """전문 에이전트 리포트를 가중 통합하고 상충 신호를 정리한다."""

    name = AgentName.SUPERVISOR

    def default_question(self, request: AnalysisRequest) -> str:
        return request.question or f"{request.ticker} 종합 분석"

    async def analyze(self, request: AnalysisRequest) -> AgentReport:
        raise NotImplementedError(
            "SupervisorAgent는 synthesize()를 사용하세요."
        )

    def synthesize(
        self,
        request: AnalysisRequest,
        reports: list[AgentReport],
        weights: AgentWeights | None = None,
    ) -> AnalysisResult:
        weights = weights or default_weights_for_horizon(request.horizon)
        normalized = weights.normalized()

        weighted_score = 0.0
        for report in reports:
            weight = normalized.get(report.agent, 0.0)
            weighted_score += SIGNAL_SCORE[report.signal] * weight * report.confidence

        if weighted_score > 0.15:
            final_signal = Signal.BULLISH
        elif weighted_score < -0.15:
            final_signal = Signal.BEARISH
        else:
            final_signal = Signal.NEUTRAL

        confidence = min(0.95, abs(weighted_score) + 0.45)
        conflicts = self._detect_conflicts(reports)
        summary = self._build_summary(request.ticker, final_signal, reports, conflicts)

        return AnalysisResult(
            ticker=request.ticker,
            question=request.question,
            horizon=request.horizon,
            final_signal=final_signal,
            confidence=confidence,
            summary=summary,
            agent_reports=reports,
            conflicts=conflicts,
        )

    def _detect_conflicts(self, reports: list[AgentReport]) -> list[str]:
        signals = {report.agent.value: report.signal for report in reports}
        conflicts: list[str] = []

        bullish = [name for name, sig in signals.items() if sig == Signal.BULLISH]
        bearish = [name for name, sig in signals.items() if sig == Signal.BEARISH]

        if bullish and bearish:
            conflicts.append(
                f"강세({', '.join(bullish)}) vs 약세({', '.join(bearish)}) 신호 공존"
            )

        fin = signals.get(AgentName.FINANCIAL.value)
        chart = signals.get(AgentName.CHART.value)
        if fin == Signal.BULLISH and chart == Signal.BEARISH:
            conflicts.append("펀더멘털은 양호하나 단기 차트는 약세")
        if fin == Signal.BEARISH and chart == Signal.BULLISH:
            conflicts.append("차트는 강세이나 펀더멘털은 부담")

        return conflicts

    def _build_summary(
        self,
        ticker: str,
        signal: Signal,
        reports: list[AgentReport],
        conflicts: list[str],
    ) -> str:
        parts = [f"{r.agent.value}: {r.signal.value}" for r in reports]
        base = f"{ticker} 종합 판단 {signal.value}. " + " | ".join(parts)
        if conflicts:
            base += f" 주의: {'; '.join(conflicts)}"
        return base
