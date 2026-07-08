"""종목 시세 조회 테스트 (KIS Open API).

실행:
    python tests/fetch_stock_quote.py
    python tests/fetch_stock_quote.py 005930
    python tests/fetch_stock_quote.py 005930 000660
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alphabet.services.kis_client import KISClient, StockQuote


def _format_change(change: int, change_rate: float) -> str:
    sign = "+" if change > 0 else ""
    return f"{sign}{change:,} ({sign}{change_rate:.2f}%)"


def _print_quote(quote: StockQuote) -> None:
    cap = f"{quote.market_cap:,}억" if quote.market_cap else "N/A"
    per = f"{quote.per:.2f}" if quote.per is not None else "N/A"
    pbr = f"{quote.pbr:.2f}" if quote.pbr is not None else "N/A"

    print()
    print("=" * 72)
    print(f"{quote.name} ({quote.ticker})")
    print("=" * 72)
    print(f"현재가   : {quote.price:,}")
    print(f"전일대비 : {_format_change(quote.change, quote.change_rate)}")
    print(f"시가     : {quote.open:,}")
    print(f"고가     : {quote.high:,}")
    print(f"저가     : {quote.low:,}")
    print(f"거래량   : {quote.volume:,}")
    print(f"시가총액 : {cap}")
    print(f"PER      : {per}")
    print(f"PBR      : {pbr}")
    print("=" * 72)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="KIS API 종목 시세 조회 테스트")
    parser.add_argument(
        "tickers",
        nargs="*",
        default=["005930"],
        help="종목 코드 (미입력 시 005930)",
    )
    parser.add_argument("--delay", type=float, default=1.0, help="종목 간 대기(초)")
    args = parser.parse_args()

    print("=== 종목 시세 조회 테스트 ===")
    print(f"종목: {', '.join(args.tickers)}")

    failed: list[str] = []

    with KISClient() as client:
        for index, ticker in enumerate(args.tickers):
            if index > 0 and args.delay > 0:
                time.sleep(args.delay)
            try:
                _print_quote(client.get_stock_quote(ticker))
            except Exception as exc:
                failed.append(ticker)
                print(f"[실패] {ticker}: {exc}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
