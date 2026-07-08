"""네이버 금융 뉴스 크롤링 테스트 (시황/전망 1~5페이지 전체, 딜레이 없음).

실행:
    python tests/crawl_naver_news.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from alphabet.services.naver_finance_news import NaverNewsArticle, fetch_outlook_news

PAGE_START = 1
PAGE_END = 5
SIMILARITY_THRESHOLD = 0.9


def _same_press_and_journalist(left: NaverNewsArticle, right: NaverNewsArticle) -> bool:
    return left.press == right.press and left.journalist == right.journalist


def _body_similarity(left: str, right: str) -> float:
    if not left.strip() or not right.strip():
        return 0.0

    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
    matrix = vectorizer.fit_transform([left, right])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0, 0])


def dedupe_articles(
    articles: list[NaverNewsArticle],
    *,
    threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[list[NaverNewsArticle], list[tuple[NaverNewsArticle, NaverNewsArticle, float]]]:
    """마지막(오래된) 기사부터 순회하며 중복을 제거한다.

    뉴스사·기자가 같고 본문 유사도가 threshold 이상이면
    오래된 기사는 유지하고 뒤에 올라온(새로운) 기사를 제거한다.
    """
    remove_flags = [False] * len(articles)
    kept_indices: list[int] = []
    removed_pairs: list[tuple[NaverNewsArticle, NaverNewsArticle, float]] = []

    for index in range(len(articles) - 1, -1, -1):
        current = articles[index]
        matched = False

        for kept_index in kept_indices:
            older = articles[kept_index]
            if not _same_press_and_journalist(current, older):
                continue

            similarity = _body_similarity(current.content, older.content)
            if similarity >= threshold:
                remove_flags[index] = True
                removed_pairs.append((current, older, similarity))
                matched = True
                break

        if not matched:
            kept_indices.append(index)

    filtered = [article for index, article in enumerate(articles) if not remove_flags[index]]
    return filtered, removed_pairs


def main() -> None:
    print("=== 네이버 뉴스 크롤링 테스트 ===")
    print(f"수집 범위: {PAGE_START}~{PAGE_END}페이지 전체 (딜레이 없음)")
    print()

    crawl_started = time.perf_counter()
    articles = fetch_outlook_news(
        limit=None,
        page_start=PAGE_START,
        page_end=PAGE_END,
        request_delay_sec=0,
    )
    crawl_elapsed = time.perf_counter() - crawl_started

    dedupe_started = time.perf_counter()
    original_count = len(articles)
    articles, removed_pairs = dedupe_articles(articles)
    dedupe_elapsed = time.perf_counter() - dedupe_started

    print(f"크롤링: {crawl_elapsed:.2f}초 / {original_count}건")
    print(
        f"중복 제거: {dedupe_elapsed:.2f}초 / {len(removed_pairs)}건 제거 "
        f"(유사도 ≥ {SIMILARITY_THRESHOLD:.0%}, 동일 뉴스사·기자)"
    )
    print(f"최종 출력: {len(articles)}건")
    print()

    if removed_pairs:
        print("제거된 기사:")
        for removed, kept, similarity in removed_pairs:
            print(
                f"  - 제거: {removed.title} "
                f"→ 유지: {kept.title} ({similarity:.0%})"
            )
        print()

    for index, article in enumerate(articles, start=1):
        print("=" * 72)
        print(f"[{index}] {article.title}")
        print(f"뉴스사: {article.press or 'N/A'}")
        print(f"기자: {article.journalist or 'N/A'}")
        print(f"URL: {article.url}")
        print("-" * 72)
        print(article.content or "(본문 없음)")
        print()


if __name__ == "__main__":
    main()
