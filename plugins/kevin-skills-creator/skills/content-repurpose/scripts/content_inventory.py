#!/usr/bin/env python3
"""콘텐츠 목록 집계 — 감사(audit)·갭 분석 리포트의 숫자를 정확히 만든다.

리포트의 개수·비율·경과 기간을 Claude가 눈으로 세면 틀리기 쉽다. 이 스크립트가 세고, Claude는 해석과 제안을 쓴다.

읽는 형식(자동 감지)
- 책 실습 형식: 1. "제목" - 2024.06 - 카테고리   (날짜·카테고리는 생략 가능, 순서 무관)
- CSV/TSV: 머리글에 제목(title)·발행일(date)·카테고리(category)·형식(format)·URL·조회수(views) 중 일부
- 마크다운 표(같은 머리글)
"... (생략) ..."·"…" 줄이 있으면 '일부 목록'으로 표시한다(분석이 일부 기준임을 리포트에 밝혀야 한다).

집계
- 카테고리별 개수·비율(편중: 1위 비율 40% 이상), 형식 단서(비교·리뷰·사용법·튜토리얼·실습형·정리·예측)
- 발행일 범위, 오늘(--today) 기준 경과 개월, N개월(--stale-months, 기본 6) 지난 항목, 마지막 발행 이후 공백, 가장 긴 발행 공백
- 시의성 항목(버전·연도·업데이트·리뷰·트렌드·예측이 들어간 제목) — 내용이 낡았을 가능성
- 중복·통합 후보(제목의 핵심 단어를 공유하는 묶음)
- 비교(--compare 경쟁 목록): 상대에만 있는 카테고리·형식 단서, 겹치는 핵심 단어

사용법
  python content_inventory.py <목록 파일 또는 -> [--today 2026-10-02] [--stale-months 6] [--compare 경쟁목록] [--json]
마지막 줄: INVENTORY DONE items=<n> partial=<yes|no>
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

# 따옴표 제목은 통째로, 따옴표 없는 제목은 앞뒤 공백이 있는 구분자에서 끊는다(GPT-4o 같은 하이픈은 제목의 일부)
ITEM = re.compile(r'^\s*(?:\d+[.)]|[-*])\s*(?:["“”](?P<qt>[^"“”]+)["“”]|(?P<ut>.+?))(?:\s*(?:-|–|—|\|)\s+(?P<rest>.+))?\s*$')
DATE = re.compile(r"(?P<y>20\d{2})[.\-/년 ]\s*(?P<m>\d{1,2})(?:[.\-/월 ]\s*(?P<d>\d{1,2}))?")
PARTIAL = re.compile(r"(\(생략\)|\.\.\.|…|이하 생략|etc\.?)")
FORMAT_HINTS = {"비교": r"비교|vs\b|VS", "리뷰": r"리뷰|후기", "사용법·가이드": r"사용법|가이드|하는 법|방법|기초", "튜토리얼·실습": r"튜토리얼|실습|따라하기|만들기|하기$|자동",
                "뉴스·정리": r"업데이트|정리|소식|뉴스(?!레터)", "전망·예측": r"트렌드|전망|예측", "개념": r"이란\??$|란\?$|개념"}
TIME_SENSITIVE = re.compile(r"(\d+(?:\.\d+)+|GPT-?\d|20\d{2}|업데이트|리뷰|트렌드|전망|예측|신기능|출시)", re.I)
STOP = {"ai", "사용법", "정리", "기초", "방법", "하는", "법", "란", "이란", "vs", "the", "for", "with", "시대", "가이드", "하기", "로", "를", "을", "의", "위한"}


def parse(text: str) -> tuple[list[dict], bool]:
    lines = text.replace("\r\n", "\n").split("\n")
    partial = any(PARTIAL.search(l) for l in lines)
    head = next((l for l in lines if l.strip()), "")
    items: list[dict] = []
    if head.count(",") >= 1 or head.count("\t") >= 1 or head.strip().startswith("|"):
        rows = [l.strip().strip("|") for l in lines if l.strip() and not re.fullmatch(r"[|\-:\s]+", l.strip())]
        delim = "\t" if "\t" in head else ("|" if head.strip().startswith("|") else ",")
        reader = csv.reader(io.StringIO("\n".join(rows)), delimiter=delim)
        hdr = [h.strip().lower() for h in next(reader)]

        def col(*names):
            return next((i for i, h in enumerate(hdr) if any(n in h for n in names)), None)
        ci = {"title": col("title", "제목"), "date": col("date", "발행", "날짜"), "category": col("category", "카테고리", "분류", "주제"),
              "format": col("format", "형식"), "url": col("url", "링크"), "views": col("view", "조회")}
        if ci["title"] is not None:
            for r in reader:
                r = [c.strip() for c in r]
                if not any(r) or PARTIAL.search(" ".join(r)):
                    continue
                get = lambda k: r[ci[k]] if ci[k] is not None and ci[k] < len(r) else None  # noqa: E731
                items.append({"title": get("title"), "date_raw": get("date"), "category": get("category"), "format": get("format"),
                              "url": get("url"), "views": get("views")})
    if not items:
        for l in lines:
            if PARTIAL.search(l) and not ITEM.match(l.replace("...", "")):
                continue
            m = ITEM.match(l)
            if not m or not (m.group("qt") or m.group("ut") or "").strip():
                continue
            title = (m.group("qt") or m.group("ut")).strip()
            parts = [p.strip() for p in re.split(r"\s+(?:-|–|—|\|)\s+", m.group("rest") or "") if p.strip()]
            d = next((p for p in parts if DATE.search(p)), None)
            cat = next((p for p in parts if p is not d and p), None)
            items.append({"title": title, "date_raw": d, "category": cat, "format": None, "url": None, "views": None})
    for it in items:
        dm = DATE.search(it["date_raw"] or "")
        it["date"] = f"{dm.group('y')}-{int(dm.group('m')):02d}" if dm else None
    return items, partial


def months_between(a: str, b: date) -> int:
    y, m = (int(x) for x in a.split("-"))
    return (b.year - y) * 12 + (b.month - m)


def tokens(title: str) -> set[str]:
    out = set()
    for w in re.findall(r"[A-Za-z][A-Za-z0-9.+\-]*|[가-힣]{2,}", title):
        w = w.lower().strip(".")
        if w not in STOP and len(w) >= 2:
            out.add(w)
    return out


def groups(items: list[dict]) -> list[dict]:
    """핵심 단어를 공유하는 제목 묶음(합집합)."""
    titles = [it["title"] for it in items]
    tok = [tokens(t) for t in titles]
    parent = list(range(len(titles)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    shared: dict[tuple, set] = {}
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            common = tok[i] & tok[j]
            if common:
                parent[find(i)] = find(j)
                shared.setdefault(tuple(sorted((i, j))), set()).update(common)
    by: dict[int, list[int]] = {}
    for i in range(len(titles)):
        by.setdefault(find(i), []).append(i)
    out = []
    for members in by.values():
        if len(members) > 1:
            words = sorted({w for (i, j), ws in shared.items() if i in members and j in members for w in ws})
            out.append({"titles": [titles[i] for i in members], "shared_words": words})
    return out


def summarize(items: list[dict], today: date, stale: int) -> dict:
    n = len(items)
    cats: dict[str, int] = {}
    for it in items:
        cats[it["category"] or "(미분류)"] = cats.get(it["category"] or "(미분류)", 0) + 1
    cat_rows = sorted(({"category": k, "count": v, "share": round(v / n, 3)} for k, v in cats.items()), key=lambda r: (-r["count"], r["category"]))
    fmt: dict[str, int] = {}
    for it in items:
        for name, pat in FORMAT_HINTS.items():
            if re.search(pat, it["title"] or "", re.I) or (it["format"] and re.search(pat, it["format"], re.I)):
                fmt[name] = fmt.get(name, 0) + 1
    dated = sorted((it for it in items if it["date"]), key=lambda it: it["date"])
    res = {"items": n, "categories": cat_rows, "top_category": cat_rows[0]["category"] if cat_rows else None,
           "top_share": cat_rows[0]["share"] if cat_rows else 0, "concentrated": bool(cat_rows and cat_rows[0]["share"] >= 0.4),
           "format_hints": fmt, "today": today.isoformat(), "overlap_groups": groups(items),
           "time_sensitive": [it["title"] for it in items if TIME_SENSITIVE.search(it["title"] or "")]}
    if dated:
        res["date_range"] = [dated[0]["date"], dated[-1]["date"]]
        res["months_since_last"] = months_between(dated[-1]["date"], today)
        res["stale_months"] = stale
        res["stale"] = [{"title": it["title"], "date": it["date"], "months": months_between(it["date"], today)}
                        for it in dated if months_between(it["date"], today) >= stale]
        gaps = [(months_between(a["date"], date(int(b["date"][:4]), int(b["date"][5:7]), 1)), a["date"], b["date"])
                for a, b in zip(dated, dated[1:])]
        res["largest_gap"] = max(gaps)[0:3] if gaps else None
        res["undated"] = n - len(dated)
    else:
        res["date_range"] = None
        res["undated"] = n
    return res


def compare(mine: list[dict], other: list[dict]) -> dict:
    mc = {(it["category"] or "").strip() for it in mine}
    oc = {(it["category"] or "").strip() for it in other}
    mt = set().union(*(tokens(it["title"]) for it in mine)) if mine else set()
    ot = set().union(*(tokens(it["title"]) for it in other)) if other else set()

    def fmts(items):
        f = set()
        for it in items:
            for name, pat in FORMAT_HINTS.items():
                if re.search(pat, (it["title"] or "") + " " + (it["category"] or ""), re.I):
                    f.add(name)
        return f
    return {"only_in_other_categories": sorted(c for c in oc - mc if c), "only_in_mine_categories": sorted(c for c in mc - oc if c),
            "shared_words": sorted(mt & ot), "only_in_other_formats": sorted(fmts(other) - fmts(mine)),
            "other_titles_without_shared_words": [it["title"] for it in other if not (tokens(it["title"]) & mt)]}


def read(p: str) -> str:
    return sys.stdin.read() if p == "-" else Path(p).read_text(encoding="utf-8-sig")


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="콘텐츠 목록 집계")
    ap.add_argument("input")
    ap.add_argument("--today")
    ap.add_argument("--stale-months", type=int, default=6)
    ap.add_argument("--compare")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else date.today()
    items, partial = parse(read(a.input))
    if not items:
        print("오류: 목록 항목을 찾지 못했습니다. 한 줄에 하나씩 '1. \"제목\" - 2024.06 - 카테고리' 형식이나 CSV로 주세요.")
        return 1
    res = summarize(items, today, a.stale_months)
    res["partial"] = partial
    if a.compare:
        other, opartial = parse(read(a.compare))
        res["compare"] = compare(items, other)
        res["compare"]["other_items"] = len(other)
        res["compare"]["other_partial"] = opartial
        res["partial"] = partial or opartial
    res["parsed"] = items
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"항목 {res['items']}개{' (일부 목록)' if partial else ''}, 기준일 {res['today']}")
        print("| 카테고리 | 개수 | 비율 |\n|---|---:|---:|")
        for r in res["categories"]:
            print(f"| {r['category']} | {r['count']} | {r['share']:.0%} |")
        if res.get("date_range"):
            print(f"발행 기간 {res['date_range'][0]} ~ {res['date_range'][1]}, 마지막 발행 후 {res['months_since_last']}개월, "
                  f"{a.stale_months}개월 넘은 항목 {len(res['stale'])}개")
        print(f"편중: {res['top_category']} {res['top_share']:.0%}{' (40% 이상)' if res['concentrated'] else ''}")
        print(f"시의성 항목: {res['time_sensitive']}")
        print(f"중복·통합 후보: {[g['titles'] for g in res['overlap_groups']]}")
        if a.compare:
            c = res["compare"]
            print(f"경쟁에만 있는 카테고리: {c['only_in_other_categories']}, 형식: {c['only_in_other_formats']}")
    print(f"INVENTORY DONE items={res['items']} partial={'yes' if res['partial'] else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
