"""네이버페이증권 시황/전망 뉴스 크롤링."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

OUTLOOK_NEWS_LIST_URL = (
    "https://finance.naver.com/news/news_list.naver"
    "?mode=LSS3D&section_id=101&section_id2=258&section_id3=401"
)

STOCK_NEWS_LIST_URL = "https://finance.naver.com/item/news_news.naver?code={ticker}"

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_FINANCE_BASE = "https://finance.naver.com"
_ARTICLE_BASE = "https://n.news.naver.com/mnews/article"


_OFFICE_NAMES: dict[str, str] = {
    "001": "연합뉴스",
    "008": "머니투데이",
    "009": "매일경제",
    "011": "서울경제",
    "014": "파이낸셜뉴스",
    "015": "한국경제",
    "018": "이데일리",
    "021": "문화일보",
    "025": "중앙일보",
    "277": "아시아경제",
    "421": "뉴스1",
}


@dataclass(frozen=True)
class NaverNewsArticle:
    title: str
    content: str
    url: str
    office_id: str
    article_id: str
    press: str | None = None
    journalist: str | None = None


def _default_headers(*, referer: str | None = None) -> dict[str, str]:
    headers = {"User-Agent": _USER_AGENT}
    if referer:
        headers["Referer"] = referer
    return headers


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_body_text(body_el) -> str:
    """본문에서 문단 구분(\\n\\n)을 유지한다."""
    if body_el is None:
        return ""

    paragraphs: list[str] = []
    for line in body_el.get_text("\n", strip=True).split("\n"):
        normalized = re.sub(r"[ \t]+", " ", line).strip()
        if normalized:
            paragraphs.append(normalized)

    return "\n\n".join(paragraphs)


def _parse_press_and_journalist(
    soup: BeautifulSoup,
    *,
    office_id: str,
    content: str,
) -> tuple[str | None, str | None]:
    press: str | None = None
    journalist: str | None = None

    logo = soup.select_one(".media_end_head_top_logo img")
    if logo and logo.get("alt"):
        press = _normalize_text(logo["alt"])

    if not press:
        press_el = soup.select_one("span.media_end_head_top_press")
        if press_el:
            press = _normalize_text(press_el.get_text())

    if not press:
        press = _OFFICE_NAMES.get(office_id)

    journalist_el = soup.select_one("em.media_end_head_journalist_name")
    if journalist_el:
        journalist = _normalize_text(journalist_el.get_text())
    else:
        byline = soup.select_one(".byline")
        if byline:
            journalist = _normalize_text(byline.get_text())

    if journalist:
        journalist = re.sub(r"\s*기자\s*$", "", journalist)
        journalist = re.sub(r"\(.*\)$", "", journalist).strip()

    if not press or not journalist:
        first_paragraph = content.split("\n\n", 1)[0] if content else ""
        press2, journalist2 = _parse_press_journalist_from_content(first_paragraph)
        press = press or press2
        journalist = journalist or journalist2

    return press, journalist


def _parse_press_journalist_from_content(
    content: str,
) -> tuple[str | None, str | None]:
    if not content:
        return None, None

    match = re.match(
        r"^\((?:[^=]+=)?([^)]+)\)\s*([^\s=]+)\s*기자",
        content,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()

    match = re.match(r"^\[([^\]]+)\s+([^\s\]]+)\s*기자\]", content)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return None, None


def stock_news_list_url(ticker: str) -> str:
    return STOCK_NEWS_LIST_URL.format(ticker=ticker)


def _list_url_with_page(list_url: str, page: int) -> str:
    parsed = urlparse(list_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _parse_list_items(
    html: str,
    *,
    limit: int | None = None,
) -> list[tuple[str, str, str]]:
    soup = BeautifulSoup(html, "lxml")
    left = soup.select_one("#contentarea_left")
    if left is None:
        return []

    items: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for dd in left.select("dd.articleSubject"):
        anchor = dd.select_one("a[href*='news_read']")
        if anchor is None:
            continue

        href = urljoin(_FINANCE_BASE, anchor["href"])
        query = parse_qs(urlparse(href).query)
        office_id = query.get("office_id", [""])[0]
        article_id = query.get("article_id", [""])[0]
        if not office_id or not article_id:
            continue

        key = (office_id, article_id)
        if key in seen:
            continue
        seen.add(key)

        title = anchor.get("title") or anchor.get_text(strip=True)
        if not title:
            continue

        items.append((title, office_id, article_id))
        if limit is not None and len(items) >= limit:
            break

    return items


def _collect_list_items(
    client: httpx.Client,
    *,
    list_url: str,
    page_start: int,
    page_end: int,
    limit: int | None,
    headers: dict[str, str],
) -> list[tuple[str, str, str, str]]:
    collected: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for page in range(page_start, page_end + 1):
        page_url = _list_url_with_page(list_url, page)
        response = client.get(page_url, headers=headers)
        response.raise_for_status()
        response.encoding = "euc-kr"

        remaining = None
        if limit is not None:
            remaining = limit - len(collected)
            if remaining <= 0:
                break

        for title, office_id, article_id in _parse_list_items(
            response.text,
            limit=remaining,
        ):
            key = (office_id, article_id)
            if key in seen:
                continue
            seen.add(key)
            collected.append((page_url, title, office_id, article_id))
            if limit is not None and len(collected) >= limit:
                break

    return collected


def _fetch_article(
    client: httpx.Client,
    office_id: str,
    article_id: str,
    *,
    list_url: str,
    fallback_title: str,
) -> NaverNewsArticle:
    url = f"{_ARTICLE_BASE}/{office_id}/{article_id}"
    response = client.get(url, headers=_default_headers(referer=list_url))
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    title_el = soup.select_one(
        "#title_area span, h2.media_end_head_headline, #articleTitle"
    )
    body_el = soup.select_one("#dic_area, #newsct_article, .newsct_article")

    title = _normalize_text(title_el.get_text()) if title_el else fallback_title
    content = _extract_body_text(body_el)
    press, journalist = _parse_press_and_journalist(
        soup,
        office_id=office_id,
        content=content,
    )

    return NaverNewsArticle(
        title=title,
        content=content,
        url=url,
        office_id=office_id,
        article_id=article_id,
        press=press,
        journalist=journalist,
    )


def fetch_news(
    limit: int | None = None,
    *,
    page_start: int = 1,
    page_end: int = 1,
    list_url: str = OUTLOOK_NEWS_LIST_URL,
    request_delay_sec: float = 0.3,
) -> list[NaverNewsArticle]:
    """뉴스 목록 URL에서 제목·본문을 수집한다."""
    if page_start < 1 or page_end < page_start:
        raise ValueError("page_start는 1 이상, page_end는 page_start 이상이어야 합니다.")

    headers = _default_headers(referer=_FINANCE_BASE)

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        list_items = _collect_list_items(
            client,
            list_url=list_url,
            page_start=page_start,
            page_end=page_end,
            limit=limit,
            headers=headers,
        )
        articles: list[NaverNewsArticle] = []

        for index, (page_url, title, office_id, article_id) in enumerate(list_items):
            if index > 0 and request_delay_sec > 0:
                time.sleep(request_delay_sec)

            article = _fetch_article(
                client,
                office_id,
                article_id,
                list_url=page_url,
                fallback_title=title,
            )
            articles.append(article)

        return articles


def fetch_outlook_news(
    limit: int | None = None,
    *,
    page_start: int = 1,
    page_end: int = 1,
    request_delay_sec: float = 0.3,
) -> list[NaverNewsArticle]:
    """시황/전망 섹션 뉴스 수집."""
    return fetch_news(
        limit,
        page_start=page_start,
        page_end=page_end,
        list_url=OUTLOOK_NEWS_LIST_URL,
        request_delay_sec=request_delay_sec,
    )


def fetch_stock_news(
    ticker: str,
    limit: int | None = 5,
    *,
    page_start: int = 1,
    page_end: int = 1,
    request_delay_sec: float = 0.3,
) -> list[NaverNewsArticle]:
    """특정 종목 관련 뉴스 수집."""
    return fetch_news(
        limit,
        page_start=page_start,
        page_end=page_end,
        list_url=stock_news_list_url(ticker),
        request_delay_sec=request_delay_sec,
    )
