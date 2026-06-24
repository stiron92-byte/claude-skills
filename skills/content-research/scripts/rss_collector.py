"""
RSS 피드 수집기
관심 분야 뉴스를 RSS 피드에서 자동 수집합니다.
"""

import feedparser
import yaml
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Article:
    title: str
    link: str
    summary: str
    published: str
    source: str
    collected_at: str


def load_config(config_path: str = "config.yaml") -> dict:
    """설정 파일을 로드합니다."""
    path = Path(config_path)
    if not path.exists():
        print(f"[오류] 설정 파일을 찾을 수 없습니다: {config_path}")
        print("config.example.yaml을 복사하여 config.yaml을 만들어주세요.")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_feed(feed_url: str, max_entries: int = 10) -> list[Article]:
    """단일 RSS 피드에서 기사를 수집합니다."""
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo and not feed.entries:
            print(f"  [경고] 피드 파싱 실패: {feed_url}")
            return articles

        source_name = feed.feed.get("title", feed_url)
        now = datetime.now().isoformat()

        for entry in feed.entries[:max_entries]:
            published = ""
            if hasattr(entry, "published"):
                published = entry.published
            elif hasattr(entry, "updated"):
                published = entry.updated

            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description
            # HTML 태그 간단 제거
            summary = _strip_html(summary)
            # 요약 길이 제한
            if len(summary) > 500:
                summary = summary[:500] + "..."

            articles.append(Article(
                title=entry.get("title", "제목 없음"),
                link=entry.get("link", ""),
                summary=summary,
                published=published,
                source=source_name,
                collected_at=now,
            ))

        print(f"  [성공] {source_name}: {len(articles)}개 기사 수집")

    except Exception as e:
        print(f"  [오류] {feed_url}: {e}")

    return articles


def _strip_html(text: str) -> str:
    """간단한 HTML 태그 제거."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def collect_all_feeds(config: dict) -> list[Article]:
    """설정에 등록된 모든 RSS 피드에서 기사를 수집합니다."""
    feeds = config.get("rss_feeds", [])
    max_entries = config.get("max_entries_per_feed", 10)

    if not feeds:
        print("[경고] 등록된 RSS 피드가 없습니다. config.yaml을 확인하세요.")
        return []

    print(f"\n{'='*50}")
    print(f"RSS 수집 시작 — {len(feeds)}개 피드")
    print(f"{'='*50}")

    all_articles = []
    for feed_url in feeds:
        articles = fetch_feed(feed_url, max_entries)
        all_articles.extend(articles)

    print(f"\n총 {len(all_articles)}개 기사 수집 완료")
    return all_articles


def filter_recent(articles: list[Article], days: int = 3) -> list[Article]:
    """최근 N일 이내 기사만 필터링합니다."""
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for article in articles:
        try:
            from email.utils import parsedate_to_datetime
            pub_date = parsedate_to_datetime(article.published)
            if pub_date.replace(tzinfo=None) >= cutoff:
                recent.append(article)
        except (ValueError, TypeError):
            # 날짜 파싱 실패 시 포함 (최신일 가능성)
            recent.append(article)
    return recent


def save_articles(articles: list[Article], output_dir: str = "output") -> str:
    """수집된 기사를 JSON 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"articles_{timestamp}.json")

    data = [asdict(a) for a in articles]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"기사 저장 완료: {filepath}")
    return filepath


def load_articles(filepath: str) -> list[Article]:
    """저장된 기사 JSON 파일을 로드합니다."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Article(**item) for item in data]


if __name__ == "__main__":
    config = load_config()
    articles = collect_all_feeds(config)

    filter_days = config.get("filter_days", 3)
    if filter_days:
        articles = filter_recent(articles, days=filter_days)
        print(f"최근 {filter_days}일 이내 기사: {len(articles)}개")

    if articles:
        filepath = save_articles(articles)
        print(f"\n수집 결과가 {filepath}에 저장되었습니다.")
    else:
        print("\n수집된 기사가 없습니다.")
