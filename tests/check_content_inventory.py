#!/usr/bin/env python3
"""R4: content_inventory.py가 책 실습 8-1·8-2 목록과 CSV를 정확히 집계하는지 확인한다.

기대값은 정답표(answer_key.json의 audit_8_1·gap_8_2)다. 프롬프트 원문은 PROMPT.MD에서 그대로 읽는다.
양성 대조: 날짜 하나를 바꾼 목록에서는 경과 개월이 정답과 달라져야 한다.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repurpose_fixtures import KEY, ROOT, run_script  # noqa: E402

PROMPT_MD = ROOT / "chapter12_프롬프트 및 부록" / "PROMPT.MD"
TODAY = "2026-10-02"


def book(n: str) -> str:
    t = PROMPT_MD.read_text(encoding="utf-8")
    return re.search(r"### 💡 프롬프트 " + re.escape(n) + r"\..*?```text\n(.*?)```", t, re.S).group(1)


def run(path: Path, *extra) -> dict:
    r = run_script("content_inventory.py", path, "--today", TODAY, "--json", *extra)
    return json.loads(r.stdout[: r.stdout.rindex("INVENTORY DONE")])


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    fails: list[str] = []
    a = KEY["audit_8_1"]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        T = Path(td)
        (T / "a.txt").write_text(book("8-1"), encoding="utf-8")
        res = run(T / "a.txt")
        cats = {r["category"]: r["count"] for r in res["categories"]}
        if res["items"] != a["items"] or cats != a["categories"]:
            fails.append(f"8-1 집계 {res['items']}개 {cats}")
        if (res["top_category"], res["top_share"], res["concentrated"]) != (a["top_category"], a["top_share"], True):
            fails.append(f"편중 {res['top_category']} {res['top_share']}")
        if res["date_range"] != a["date_range"] or res["months_since_last"] != a["months_since_last_as_of_2026_10"]:
            fails.append(f"기간 {res['date_range']}, 마지막 발행 후 {res['months_since_last']}개월")
        if len(res["stale"]) != a["older_than_6_months_as_of_2026_10"]:
            fails.append(f"6개월 경과 {len(res['stale'])}")
        if sorted(res["time_sensitive"]) != sorted(a["time_sensitive"]):
            fails.append(f"시의성 {res['time_sensitive']}")
        if [sorted(g["titles"]) for g in res["overlap_groups"]] != [sorted(g) for g in a["overlap_groups_by_words"]]:
            fails.append(f"중복 후보 {res['overlap_groups']}")
        if res["partial"]:
            fails.append("8-1은 전체 목록인데 일부 목록으로 표시")
        # 8-2: 일부 목록, 경쟁에만 있는 카테고리·형식
        b = book("8-2")
        mine, comp = b.split("경쟁 채널 콘텐츠 목록:")
        (T / "m.txt").write_text(mine, encoding="utf-8")
        (T / "c.txt").write_text(comp, encoding="utf-8")
        g = run(T / "m.txt", "--compare", T / "c.txt")
        c = g["compare"]
        if not (g["partial"] and c["other_partial"]) or g["items"] != 3 or c["other_items"] != 4:
            fails.append(f"8-2 일부 목록·개수 {g['partial']} {c['other_partial']} {g['items']} {c['other_items']}")
        if not {"AI 실전 활용", "자동화 튜토리얼", "실습형"} <= set(c["only_in_other_categories"]):
            fails.append(f"경쟁에만 있는 카테고리 {c['only_in_other_categories']}")
        if "튜토리얼·실습" not in c["only_in_other_formats"] or "뉴스·정리" in c["only_in_other_formats"]:
            fails.append(f"형식 갭 {c['only_in_other_formats']}(뉴스레터를 뉴스로 오인하면 안 됨)")
        if sorted(c["other_titles_without_shared_words"]) != sorted(["AI로 부동산 투자 분석하기", "비개발자를 위한 자동화 워크플로", "GPT로 뉴스레터 자동 발행하는 법"]):
            fails.append(f"겹치지 않는 경쟁 제목 {c['other_titles_without_shared_words']}")
        # CSV·마크다운 표 입력
        (T / "l.csv").write_text("제목,발행일,카테고리,조회수\nGPT-4o 업데이트 정리,2024-10-03,AI 뉴스,1200\n에이전트 AI란?,2025-04-11,AI 개념,800\n", encoding="utf-8")
        cs = run(T / "l.csv")
        if cs["items"] != 2 or cs["date_range"] != ["2024-10", "2025-04"] or cs["parsed"][0]["views"] != "1200":
            fails.append(f"CSV {cs['items']} {cs['date_range']}")
        (T / "t.md").write_text("| 제목 | 날짜 | 카테고리 |\n|---|---|---|\n| A 비교 | 2025.01 | 도구 |\n| B 비교 | 2025.02 | 도구 |\n", encoding="utf-8")
        tb = run(T / "t.md")
        if tb["items"] != 2 or not tb["overlap_groups"]:
            fails.append(f"마크다운 표 {tb['items']} {tb['overlap_groups']}")
        # 양성 대조: 마지막 날짜를 바꾸면 경과 개월이 달라져야 한다
        (T / "x.txt").write_text(book("8-1").replace("2025.04", "2026.08"), encoding="utf-8")
        if run(T / "x.txt")["months_since_last"] == a["months_since_last_as_of_2026_10"]:
            fails.append("양성 대조 실패: 날짜를 바꿔도 경과 개월이 같다")
        (T / "e.txt").write_text("목록 없음\n", encoding="utf-8")
        if run_script("content_inventory.py", T / "e.txt").returncode == 0:
            fails.append("항목 없는 입력을 오류로 처리하지 않았다")
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"CONTENT INVENTORY FAILED ({len(fails)})")
        return 1
    print("CONTENT INVENTORY OK — 책 실습 8-1(10개·AI 도구 50%·18개월 공백·시의성 3)·8-2(일부 목록·갭 카테고리) 정답 일치, CSV·표 입력, 양성 대조")
    return 0


if __name__ == "__main__":
    sys.exit(main())
