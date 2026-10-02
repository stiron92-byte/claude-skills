#!/usr/bin/env python3
"""R1: content-repurpose 실습 원본·정답표를 확인한다.

- 생성기가 같은 원본·정답표를 다시 만드는가(재현성)
- 정답표의 숫자·핵심 메시지 단어·단서가 원본에서 독립적으로 확인되는가
- 카탈로그에 실습 입력·정답표 세트가 있고, 제3자 녹취(8장 유튜브 스크립트)는 실습 입력으로 배포하지 않는가
양성 대조: 정답표에 원본에 없는 숫자를 넣으면 대조가 실패해야 한다.
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repurpose_fixtures import KEY, ROOT, SOURCE  # noqa: E402

CATALOG = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/catalog.json"


def check_key(k: dict, src: str) -> list[str]:
    p = []
    flat = re.sub(r"\s+", " ", src)
    for n in k["numbers"]:
        if n not in flat:
            p.append(f"숫자 '{n}'가 원본에 없다")
    for c in k["core_messages"]:
        if not any(w in flat for w in c["any"]):
            p.append(f"핵심 메시지 '{c['key']}' 단어가 원본에 없다")
    if "유료화는 하지 않았습니다" not in flat or "광고 제안이 2건" not in flat or "분야마다" not in flat:
        p.append("단서(유료화 안 함·광고 2건 거절·분야마다 다름)가 원본에 없다")
    if k["title"] not in src.splitlines()[0]:
        p.append("제목 불일치")
    return p


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    fails: list[str] = []
    r = subprocess.run([sys.executable, str(ROOT / "tools/dev/make_repurpose_practice.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if "REPRODUCIBLE" not in r.stdout:
        fails.append(f"재현 불가: {r.stdout[-200:]} {r.stderr[-200:]}")
    src = SOURCE.read_text(encoding="utf-8")
    fails += check_key(KEY["repurpose"], src)
    bad = copy.deepcopy(KEY["repurpose"])
    bad["numbers"].append("월 150만 원")
    if not check_key(bad, src):
        fails.append("양성 대조 실패: 원본에 없는 숫자를 넣은 정답표가 통과했다")
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    sets = [s for s in cat["sets"] if s["skill"] == "content-repurpose"]
    inp = [s for s in sets if s["kind"] == "input"]
    if not any(SOURCE.name in " ".join(s["files"]) for s in inp):
        fails.append("카탈로그에 실습 원본 세트가 없다")
    if not any("answer_key.json" in " ".join(s["files"]) for s in sets if s["kind"] == "reference-output"):
        fails.append("카탈로그에 정답표 세트가 없다")
    if any("유출" in f for s in inp for f in s["files"]):
        fails.append("제3자 녹취(유튜브 스크립트)가 실습 입력으로 배포된다")
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"REPURPOSE PRACTICE FAILED ({len(fails)})")
        return 1
    print(f"REPURPOSE PRACTICE OK — 원본 재현, 숫자 {len(KEY['repurpose']['numbers'])}개·핵심 메시지 3개·단서 원본 대조, 카탈로그, 양성 대조 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
