from __future__ import annotations

from dataclasses import dataclass

from alphabet.schemas.common import Signal


@dataclass
class SentimentResult:
    label: str
    score: float
    signal: Signal


class SentimentAnalyzer:
    """뉴스·공시 텍스트 감성 분석 (FinBERT 등 연동 예정)."""

    def analyze(self, text: str) -> SentimentResult:
        raise NotImplementedError("SentimentAnalyzer.analyze() 미구현")

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult]:
        raise NotImplementedError("SentimentAnalyzer.analyze_batch() 미구현")

    @staticmethod
    def aggregate(results: list[SentimentResult]) -> Signal:
        raise NotImplementedError("SentimentAnalyzer.aggregate() 미구현")
