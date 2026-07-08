"""HuggingFace 공통 유틸리티 (lazy import)."""

__all__ = ["HFClient", "SentimentAnalyzer", "get_hf_client"]


def __getattr__(name: str):
    if name == "HFClient":
        from alphabet.ml.hf_client import HFClient

        return HFClient
    if name == "get_hf_client":
        from alphabet.ml.hf_client import get_hf_client

        return get_hf_client
    if name == "SentimentAnalyzer":
        from alphabet.ml.sentiment import SentimentAnalyzer

        return SentimentAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
