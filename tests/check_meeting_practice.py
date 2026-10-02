#!/usr/bin/env python3
"""M1: 회의록 실습 입력(녹음 3개 + 텍스트 녹취록 1개)과 정답표를 확인한다.

- 생성기가 같은 녹취록·정답표를 다시 만드는가(재현성)
- 텍스트 정답표의 모든 사실(참석자·결정 문구·담당자·숫자·다음 회의)이 녹취록에서 독립적으로 확인되는가
- 번복된 안(3월 23일)이 녹취에 있고, 최종 결정(3월 30일)이 그보다 뒤에 나오는가
- 녹음 정답표가 세 녹음 모두를 다루고 참석자가 녹음 README와 같은가
- 카탈로그에 텍스트 입력·정답표 세트가 있는가
양성 대조: 정답표를 일부러 틀리게 바꾼 사본은 같은 대조에서 실패해야 한다.
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _meeting_fixtures import AUDIO, KEY, ROOT, TEXT  # noqa: E402

CATALOG = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/catalog.json"


def check_text_key(k: dict, body: str) -> list[str]:
    p = []
    flat = re.sub(r"\s+", " ", body)
    head = body.splitlines()[:4]
    if not all(a in head[2] for a in k["attendees"]):
        p.append(f"머리글 참석자 {head[2]} ≠ {k['attendees']}")
    if k["date"].replace("-", ".") not in head[1]:
        p.append(f"머리글 날짜 {head[1]} ≠ {k['date']}")
    for ab in k["absent"]:
        if ab[1:] not in flat or "휴가" not in flat:
            p.append(f"불참자 {ab} 언급 없음")
    for d in k["decisions"]:
        for s in d["must"]:
            if s not in flat:
                p.append(f"결정 '{d['key']}'의 '{s}'가 녹취에 없다")
    for sup in k["superseded"]:
        date = sup.split()[0] + " " + sup.split()[1]
        final = k["decisions"][0]["must"][0]
        if date not in flat or flat.rfind(final) < flat.find(date):
            p.append(f"번복 순서: '{date}' 뒤에 '{final}'가 나오지 않는다")
    for a in k["actions"]:
        o = a["owner"]
        if o != "미정" and not o.startswith("미정") and o not in body:
            p.append(f"할 일 '{a['task']}' 담당자 {o}가 녹취에 없다")
        if a["due"] not in ("미정",) and not a["due"].startswith(("오픈", "다음")) and a["due"] not in flat:
            p.append(f"할 일 '{a['task']}' 기한 {a['due']}가 녹취에 없다")
    for n in k["numbers"]:
        if n not in flat:
            p.append(f"숫자 {n}가 녹취에 없다")
    nm = re.search(r"(\d+)월 (\d+)일", k["next_meeting"].replace("2026-03-16", "3월 16일"))
    if not nm or f"{nm.group(1)}월 {nm.group(2)}일" not in flat:
        p.append("다음 회의 날짜가 녹취에 없다")
    return p


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    fails: list[str] = []
    r = subprocess.run([sys.executable, str(ROOT / "tools/dev/make_meeting_practice.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if "REPRODUCIBLE" not in r.stdout:
        fails.append(f"재현 불가: {r.stdout[-200:]} {r.stderr[-200:]}")
    body = TEXT.read_text(encoding="utf-8")
    fails += check_text_key(KEY["text"], body)
    # 양성 대조
    bad = copy.deepcopy(KEY["text"])
    bad["decisions"][0]["must"] = ["3월 31일"]
    bad["actions"][0]["owner"] = "홍길동"
    bad["numbers"].append("5,000만")
    if len(check_text_key(bad, body)) < 3:
        fails.append("양성 대조 실패: 틀린 정답표가 대조를 통과했다")
    # 녹음 정답표
    readme = (AUDIO / "README.md").read_text(encoding="utf-8")
    audio = KEY["audio"]
    if sorted(audio) != sorted(p.name for p in AUDIO.glob("*.mp3")):
        fails.append(f"녹음 정답표 대상 {sorted(audio)}")
    for name, k in audio.items():
        for a in k["attendees"]:
            if a not in readme:
                fails.append(f"{name}: 참석자 {a}가 README에 없다")
        if not k["decisions"] or not k["actions"] or "stt_traps" not in k:
            fails.append(f"{name}: 결정·할 일·STT 함정이 비었다")
        for a in k["actions"]:
            if a["owner"] not in k["attendees"] and not a["owner"].startswith("미정"):
                fails.append(f"{name}: 담당자 {a['owner']}가 참석자가 아니다")
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    ids = {s["id"]: s for s in cat["sets"]}
    if ids.get("meeting-text", {}).get("kind") != "input" or "inputs/마케팅주간회의_녹취록.txt" not in " ".join(ids.get("meeting-text", {}).get("files", [])):
        fails.append("카탈로그에 텍스트 녹취록 입력 세트가 없다")
    if ids.get("meeting-answer-key", {}).get("kind") != "reference-output":
        fails.append("카탈로그에 정답표 세트가 없다")
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"MEETING PRACTICE FAILED ({len(fails)})")
        return 1
    n_act = len(KEY["text"]["actions"]) + sum(len(k["actions"]) for k in audio.values())
    print(f"MEETING PRACTICE OK — 텍스트 녹취록 재현, 정답표 사실 독립 대조, 녹음 3개 정답표(할 일 총 {n_act}개), 카탈로그, 양성 대조 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
