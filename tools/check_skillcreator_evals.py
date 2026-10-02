#!/usr/bin/env python3
"""P7 오라클: skill-creator 형식 evals.json 검사.

- <스킬>/evals/evals.json 존재, skill_name 일치, id 고유
- eval마다 prompt·expected_output·expectations(3개 이상) 존재
- files 경로가 저장소에 실제로 있다
- 책 실습 프롬프트 매핑: doc-automation은 2-3, hwpx-editor는 2-6·2-7을 포함하고 프롬프트 문구가 PROMPT.MD와 같다
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ROOT, force_utf8_stdout, skill_dir  # noqa: E402

PROMPT_MD = ROOT / "chapter12_프롬프트 및 부록" / "PROMPT.MD"
REQUIRED_BOOK = {"doc-automation": ["2-3"], "hwpx-editor": ["2-6", "2-7"], "content-repurpose": ["8-1", "8-2"]}


def book_prompts() -> dict[str, str]:
    text = PROMPT_MD.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"### 💡 프롬프트 (\d+-\d+)\..*?```text\n(.*?)```", text, re.S):
        out[m.group(1)] = " ".join(m.group(2).split())
    return out


def main(argv: list[str]) -> int:
    force_utf8_stdout()
    problems: list[str] = []
    book = book_prompts()
    for skill in argv:
        p = skill_dir(skill) / "evals" / "evals.json"
        if not p.is_file():
            problems.append(f"{skill}: evals.json 없음")
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("skill_name") != skill:
            problems.append(f"{skill}: skill_name 불일치")
        evals = data.get("evals", [])
        ids = [e.get("id") for e in evals]
        if len(set(ids)) != len(ids) or not evals:
            problems.append(f"{skill}: id 중복 또는 eval 없음")
        for e in evals:
            tag = f"{skill}#{e.get('id')}"
            for k in ("prompt", "expected_output"):
                if not str(e.get(k, "")).strip():
                    problems.append(f"{tag}: {k} 없음")
            if len(e.get("expectations", [])) < 3:
                problems.append(f"{tag}: expectations 3개 미만")
            for f in e.get("files", []):
                if not (ROOT / f).exists():
                    problems.append(f"{tag}: 입력 파일 없음 {f}")
        mapped = {e.get("book_prompt"): " ".join(e["prompt"].split()) for e in evals if e.get("book_prompt")}
        for bp in REQUIRED_BOOK.get(skill, []):
            if bp not in mapped:
                problems.append(f"{skill}: 책 실습 프롬프트 {bp} 없음")
            elif bp in book and mapped[bp] != book[bp]:
                problems.append(f"{skill}: 프롬프트 {bp} 문구가 PROMPT.MD와 다름")
    for x in problems:
        print("FAIL:", x)
    if problems:
        return 1
    print(f"checked: {', '.join(argv)}; book prompts parsed: {len(book)}")
    print("SKILLCREATOR EVALS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
