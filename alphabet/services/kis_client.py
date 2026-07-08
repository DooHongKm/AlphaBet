from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from alphabet.config import Settings, get_settings
from alphabet.schemas.market import PriceBar

REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"
MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"

TOKEN_MIN_INTERVAL_SEC = 61
TOKEN_TTL_SEC = 23 * 60 * 60
TOKEN_RETRY_WAIT_SEC = 61
API_RETRY_WAIT_SEC = 5
RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}


@dataclass
class StockQuote:
    ticker: str
    name: str
    price: int
    change: int
    change_rate: float
    open: int
    high: int
    low: int
    volume: int
    market_cap: int | None = None
    per: float | None = None
    pbr: float | None = None


class KISClient:
    """한국투자증권 Open API 클라이언트 (조회 전용)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.kis_app_key or not self.settings.kis_app_secret:
            raise ValueError("KIS_APP_KEY, KIS_APP_SECRET 환경 변수가 필요합니다.")

        self.base_url = MOCK_BASE_URL if self.settings.kis_is_mock else REAL_BASE_URL
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._client = httpx.Client(timeout=30.0)
        self._token_cache_path = self.settings.db_path.parent / "kis_token_cache.json"
        self._load_token_cache()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> KISClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _load_token_cache(self) -> None:
        if not self._token_cache_path.exists():
            return
        try:
            data = json.loads(self._token_cache_path.read_text(encoding="utf-8"))
            if data.get("app_key") != self.settings.kis_app_key:
                return
            expires_at = float(data.get("expires_at", 0))
            if time.time() < expires_at and data.get("access_token"):
                self._access_token = data["access_token"]
                self._token_expires_at = expires_at
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return

    def _save_token_cache(self) -> None:
        if not self._access_token:
            return
        self._token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "app_key": self.settings.kis_app_key,
            "access_token": self._access_token,
            "expires_at": self._token_expires_at,
            "issued_at": time.time(),
        }
        self._token_cache_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    def _token_request_cooldown(self) -> None:
        if not self._token_cache_path.exists():
            return
        try:
            data = json.loads(self._token_cache_path.read_text(encoding="utf-8"))
            issued_at = float(data.get("issued_at", 0))
            elapsed = time.time() - issued_at
            wait = TOKEN_MIN_INTERVAL_SEC - elapsed
            if wait > 0:
                time.sleep(wait)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return

    def _headers(self, tr_id: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._get_access_token()}",
            "appkey": self.settings.kis_app_key,
            "appsecret": self.settings.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def _get_access_token(self, max_retries: int = 3) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        self._load_token_cache()
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.settings.kis_app_key,
            "appsecret": self.settings.kis_app_secret,
        }

        last_error: Exception | None = None
        for attempt in range(max_retries):
            self._token_request_cooldown()
            try:
                response = self._client.post(url, json=body)
                if response.status_code in RETRYABLE_STATUS:
                    time.sleep(TOKEN_RETRY_WAIT_SEC * (attempt + 1))
                    continue
                response.raise_for_status()
                data = response.json()
                if "access_token" not in data:
                    raise RuntimeError(f"토큰 발급 실패: {data}")

                self._access_token = data["access_token"]
                self._token_expires_at = time.time() + TOKEN_TTL_SEC
                self._save_token_cache()
                return self._access_token
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in RETRYABLE_STATUS:
                    time.sleep(TOKEN_RETRY_WAIT_SEC * (attempt + 1))
                    continue
                raise

        raise RuntimeError(f"토큰 발급 실패 (재시도 {max_retries}회): {last_error}")

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, str] | None = None,
        max_retries: int = 5,
    ) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._client.request(method, url, headers=headers, params=params)
                if response.status_code in RETRYABLE_STATUS:
                    wait = API_RETRY_WAIT_SEC * (attempt + 1)
                    if response.status_code == 403:
                        wait = max(wait, TOKEN_RETRY_WAIT_SEC)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in RETRYABLE_STATUS:
                    wait = API_RETRY_WAIT_SEC * (attempt + 1)
                    if exc.response.status_code == 403:
                        wait = max(wait, TOKEN_RETRY_WAIT_SEC)
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"API 요청 실패 (재시도 {max_retries}회): {last_error}")

    def get_stock_quote(
        self,
        ticker: str,
        max_retries: int = 5,
    ) -> StockQuote:
        """주식 현재가 시세 조회 (FHKST01010100)."""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
        }

        response = self._request_with_retry(
            "GET",
            url,
            headers=self._headers("FHKST01010100"),
            params=params,
            max_retries=max_retries,
        )
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"[{ticker}] 시세 조회 실패: {data.get('msg1', data)}")

        return self._parse_quote(ticker, data["output"])

    def get_daily_chart(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        period: str = "D",
        adjusted: bool = True,
        max_retries: int = 5,
    ) -> list[PriceBar]:
        """국내주식 기간별 시세 (FHKST03010100). 1회 최대 100봉."""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "1" if adjusted else "0",
        }

        response = self._request_with_retry(
            "GET",
            url,
            headers=self._headers("FHKST03010100"),
            params=params,
            max_retries=max_retries,
        )
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"[{ticker}] 일봉 조회 실패: {data.get('msg1', data)}")

        return self._parse_daily_bars(data.get("output2", []))

    def get_daily_bars_years(
        self,
        ticker: str,
        years: int = 5,
        delay_sec: float = 1.0,
        chunk_calendar_days: int = 140,
    ) -> list[PriceBar]:
        """장기 일봉을 100봉 제한에 맞춰 분할 조회한다."""
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)
        bars_by_date: dict[date, PriceBar] = {}

        chunk_end = end_date
        while chunk_end >= start_date:
            chunk_start = max(start_date, chunk_end - timedelta(days=chunk_calendar_days))
            chunk_bars = self.get_daily_chart(ticker, chunk_start, chunk_end)
            for bar in chunk_bars:
                bars_by_date[bar.date.date()] = bar

            if chunk_start <= start_date:
                break
            chunk_end = chunk_start - timedelta(days=1)
            if delay_sec > 0:
                time.sleep(delay_sec)

        return sorted(bars_by_date.values(), key=lambda bar: bar.date)

    def get_stock_quotes(
        self,
        tickers: list[str],
        delay_sec: float = 1.0,
        skip_errors: bool = False,
    ) -> list[StockQuote]:
        quotes: list[StockQuote] = []
        for ticker in tickers:
            try:
                quotes.append(self.get_stock_quote(ticker))
            except Exception:
                if skip_errors:
                    continue
                raise
            if delay_sec > 0:
                time.sleep(delay_sec)
        return quotes

    @staticmethod
    def _parse_daily_bars(rows: list[dict[str, Any]]) -> list[PriceBar]:
        bars: list[PriceBar] = []
        for row in rows:
            raw_date = row.get("stck_bsop_date")
            if not raw_date:
                continue
            bars.append(
                PriceBar(
                    date=datetime.strptime(str(raw_date), "%Y%m%d"),
                    open=float(row.get("stck_oprc") or 0),
                    high=float(row.get("stck_hgpr") or 0),
                    low=float(row.get("stck_lwpr") or 0),
                    close=float(row.get("stck_clpr") or 0),
                    volume=float(row.get("acml_vol") or 0),
                )
            )
        return bars

    @staticmethod
    def _parse_quote(ticker: str, output: dict[str, Any]) -> StockQuote:
        def _int(key: str, default: int = 0) -> int:
            value = output.get(key, default)
            return int(value) if value not in (None, "") else default

        def _float(key: str) -> float | None:
            value = output.get(key)
            if value in (None, ""):
                return None
            return float(value)

        market_cap_raw = output.get("hts_avls")
        market_cap = int(market_cap_raw) if market_cap_raw not in (None, "") else None

        return StockQuote(
            ticker=ticker,
            name=output.get("hts_kor_isnm") or ticker,
            price=_int("stck_prpr"),
            change=_int("prdy_vrss"),
            change_rate=float(output.get("prdy_ctrt", 0) or 0),
            open=_int("stck_oprc"),
            high=_int("stck_hgpr"),
            low=_int("stck_lwpr"),
            volume=_int("acml_vol"),
            market_cap=market_cap,
            per=_float("per"),
            pbr=_float("pbr"),
        )
