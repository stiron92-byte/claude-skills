"""build_deck / verify_deck 테스트 공용 fixture."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/kevin-skills-book/skills/doc-automation/scripts"
SAMPLES = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/doc-automation"

SOURCE_TEXT = """# S01 — 주간매출.csv
이번 주 매출 4,520만 원, 지난주 3,675만 원.
채널별: 쿠팡 1,800만, 스마트스토어 1,520만, 자사몰 1,200만.
평균 객단가 32,450원, 반품률 2.8%.
"""


def make_sources(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / "S01.md").write_text(SOURCE_TEXT, encoding="utf-8")
    (d / "sources.json").write_text(json.dumps([{"id": "S01", "file": "주간매출.csv", "path": "x", "kind": "table",
                                                 "chars": len(SOURCE_TEXT), "md": "S01.md", "note": ""}],
                                               ensure_ascii=False), encoding="utf-8")
    return d


def full_outline(logo: str | None = None) -> dict:
    return {
        "meta": {"title": "주간 매출 보고", "subtitle": "9월 4주차", "audience": "팀장", "date": "2026-09-28",
                 "author": "영업기획팀", "logo": logo},
        "derived": [{"value": "23%", "formula": "(4520-3675)/3675", "inputs": ["S01: 4,520만", "S01: 3,675만"]}],
        "given": [],
        "slides": [
            {"type": "title"},
            {"type": "agenda", "items": ["핵심 요약", "채널별 실적", "다음 주 계획"]},
            {"type": "kpi", "headline": "매출이 전주 대비 23% 늘었다",
             "kpis": [{"label": "주간 매출", "value": "4,520만 원", "delta": "+23%"},
                      {"label": "객단가", "value": "32,450원"}, {"label": "반품률", "value": "2.8%"}],
             "takeaway": "쿠팡이 성장을 이끌었다", "sources": ["S01"]},
            {"type": "chart", "headline": "쿠팡 비중이 가장 크다",
             "chart": {"kind": "column", "categories": ["쿠팡", "스마트스토어", "자사몰"],
                       "series": [{"name": "매출(만 원)", "values": [1800, 1520, 1200]}], "unit": "만 원"},
             "sources": ["S01"]},
            {"type": "table", "headline": "채널별 매출",
             "table": {"columns": ["채널", "매출(만 원)"], "rows": [["쿠팡", "1,800"], ["스마트스토어", "1,520"], ["자사몰", "1,200"]]},
             "sources": ["S01"]},
            {"type": "section", "headline": "다음 주 계획"},
            {"type": "two_column", "headline": "잘된 점과 개선할 점",
             "left": {"title": "잘된 점", "bullets": ["쿠팡 기획전 효과"]},
             "right": {"title": "개선할 점", "bullets": ["자사몰 유입 감소"]}, "sources": ["S01"]},
            {"type": "bullets", "headline": "자사몰 유입을 회복해야 한다",
             "bullets": ["검색 광고 재개", {"text": "키워드 재선정", "level": 1}, "재구매 쿠폰"], "notes": "발표 메모"},
            {"type": "closing", "headline": "요청 사항", "bullets": ["광고 예산 승인"], "contact": "영업기획팀"},
        ],
    }


def write(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
