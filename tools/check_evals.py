#!/usr/bin/env python3
"""G8 오라클: claude plugin eval 케이스 골격의 구조를 정적으로 검사한다.

이 검사는 '문서화된 형식을 따르는가'만 본다. 실제 런타임 실행 검증은 별도(G9)다.

규칙
- 모든 스킬(플러그인 구성 기준)에 그 스킬을 발화 대상으로 하는 케이스가 1개 이상
- 각 케이스: prompt.md(frontmatter 키는 알려진 것만, 본문 비어 있지 않음) + graders/*.md 1개 이상
- grader type은 문서의 6종 중 하나이고 type별 필수 필드를 가짐(llm은 루브릭 본문 필수)
- 각 케이스에 점수 대상 grader(tool_used: Skill 외)가 1개 이상
- 정규식 필드는 파이썬 re로 컴파일 가능
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import PLUGIN_LAYOUT, PLUGINS_DIR, force_utf8_stdout, parse_frontmatter, read_text  # noqa: E402

PROMPT_KEYS = {"max_turns", "timeout_seconds", "allowed_tools", "runs", "tags", "model", "env"}
GRADER_REQUIRED = {
    "regex": ["pattern"],
    "tool_used": ["tool"],
    "tool_order": ["before", "after"],
    "file_exists": ["path"],
    "llm": [],
    "baseline": [],
}
REGEX_FIELDS = {"pattern", "input_match"}


def main() -> int:
    force_utf8_stdout()
    problems: list[str] = []
    fired: dict[str, int] = {s: 0 for skills in PLUGIN_LAYOUT.values() for s in skills}
    n_cases = 0
    for plugin, skills in PLUGIN_LAYOUT.items():
        ev = PLUGINS_DIR / plugin / "evals"
        cases = sorted(p for p in ev.iterdir() if p.is_dir() and p.name != "results") if ev.is_dir() else []
        if not cases:
            problems.append(f"{plugin}: evals/ 케이스 없음")
        for c in cases:
            n_cases += 1
            pm = c / "prompt.md"
            if not pm.is_file():
                problems.append(f"{c.name}: prompt.md 없음")
                continue
            fm, body, errs = parse_frontmatter(read_text(pm))
            problems += [f"{c.name}/prompt.md: {e}" for e in errs]
            for k in fm:
                if k not in PROMPT_KEYS:
                    problems.append(f"{c.name}/prompt.md: 알 수 없는 키 {k}")
            if not body.strip():
                problems.append(f"{c.name}/prompt.md: 요청 본문 비어 있음")
            graders = sorted((c / "graders").glob("*.md")) if (c / "graders").is_dir() else []
            if not graders:
                problems.append(f"{c.name}: graders 없음")
            scoring = 0
            for g in graders:
                gfm, gbody, gerrs = parse_frontmatter(read_text(g))
                problems += [f"{c.name}/{g.name}: {e}" for e in gerrs]
                t = gfm.get("type")
                if t not in GRADER_REQUIRED:
                    problems.append(f"{c.name}/{g.name}: 알 수 없는 type {t!r}")
                    continue
                for req in GRADER_REQUIRED[t]:
                    if not gfm.get(req):
                        problems.append(f"{c.name}/{g.name}: {t}에 {req} 없음")
                if t == "llm" and not gbody.strip():
                    problems.append(f"{c.name}/{g.name}: llm 루브릭 본문 없음")
                for f in REGEX_FIELDS & set(gfm):
                    try:
                        re.compile(gfm[f])
                    except re.error as e:
                        problems.append(f"{c.name}/{g.name}: {f} 정규식 오류 {e}")
                is_skill_fired = t == "tool_used" and gfm.get("tool") == "Skill"
                if is_skill_fired:
                    for s in fired:
                        if re.search(gfm.get("input_match", ""), f'"skill": "{plugin}:{s}"'):
                            if s not in skills:
                                problems.append(f"{c.name}: 다른 플러그인 스킬 {s}을 발화 대상으로 지정")
                            fired[s] += 1
                else:
                    scoring += 1
            if graders and scoring == 0:
                problems.append(f"{c.name}: 점수 대상 grader 없음(skill-fired만 있음)")
    for s, n in fired.items():
        if n == 0:
            problems.append(f"{s}: 이 스킬을 발화 대상으로 하는 케이스 없음")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print(f"{n_cases} cases, skills covered: {sum(1 for n in fired.values() if n)}/{len(fired)}")
    print("EVALS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
