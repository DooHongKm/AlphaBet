from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Signal(StrEnum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


class Horizon(StrEnum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class AgentName(StrEnum):
    FINANCIAL = "financial"
    CHART = "chart"
    MACRO = "macro"
    NEWS = "news"
    SUPERVISOR = "supervisor"


class Evidence(BaseModel):
    source: str
    metric: str | None = None
    value: str | None = None
    detail: str | None = None


class AnalysisRequest(BaseModel):
    ticker: str
    market: str = "KR"  # KR | US
    question: str | None = None
    horizon: Horizon = Horizon.MEDIUM
    locale: str = "ko"


class AgentReport(BaseModel):
    agent: AgentName
    signal: Signal
    confidence: float = Field(ge=0.0, le=1.0)
    horizon: Horizon
    summary: str
    key_points: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    ticker: str
    question: str | None
    horizon: Horizon
    final_signal: Signal
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    agent_reports: list[AgentReport]
    conflicts: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
