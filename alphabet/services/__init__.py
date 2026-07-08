"""외부 데이터 소스 접근 레이어."""

from alphabet.services.financial_data import FinancialDataService
from alphabet.services.kis_client import KISClient, StockQuote
from alphabet.services.macro_data import MacroDataService
from alphabet.services.market_data import MarketDataService
from alphabet.services.naver_finance_news import (
    NaverNewsArticle,
    fetch_news,
    fetch_outlook_news,
    fetch_stock_news,
)
from alphabet.services.news_data import NewsDataService, NewsItem

__all__ = [
    "FinancialDataService",
    "KISClient",
    "MacroDataService",
    "MarketDataService",
    "NaverNewsArticle",
    "NewsDataService",
    "NewsItem",
    "StockQuote",
    "fetch_news",
    "fetch_outlook_news",
    "fetch_stock_news",
]
