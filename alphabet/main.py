"""AlphaBet CLI 진입점."""

import argparse
import asyncio
import json

from alphabet.orchestrator.pipeline import run_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="AlphaBet 멀티 에이전트 주식 분석")
    parser.add_argument("ticker", help="종목 코드 (예: 005930, AAPL)")
    parser.add_argument("-q", "--question", help="사용자 질문", default=None)
    parser.add_argument("-m", "--market", choices=["KR", "US"], default="KR")
    parser.add_argument(
        "--hf",
        action="store_true",
        help="뉴스 감성 분석에 HuggingFace 사용",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_analysis(
            ticker=args.ticker,
            question=args.question,
            market=args.market,
            use_hf_for_news=args.hf,
        )
    )
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
