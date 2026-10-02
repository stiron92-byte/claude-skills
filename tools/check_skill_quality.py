#!/usr/bin/env python3
"""Phase 1 스킬 품질 규약 검사 (계획서 §3.5, docs/templates/SKILL.template.md).

Phase 1에서 고도화를 마친 스킬에 적용한다(baseline 없이 엄격하게).

SKILL.md
- name = 디렉터리명, description 300~1,024자, 경계 문구("쓰지 않") 포함, metadata.version 존재
- 본문 500줄 이하, 필수 섹션(언제 쓰는가 / 시작 전에 / 워크플로 / 건너뛰기 쉬운 단계 / 맞춤 / 참고)
- 워크플로 체크리스트("- [ ]") 존재
- 본문이 언급하는 references/·scripts/·templates/ 파일이 실제로 존재
- 정적 검증기(validate_skills) 위반 0건(경고 포함)
README.md
- 필수 섹션(하는 일 / 데모 / 요구사항 / 지원 환경 / 커스터마이즈 포인트 / 데이터 흐름 / 변경 이력)
- 커스터마이즈 포인트 표에 L0~L2 행이 1개 이상

사용법: python tools/check_skill_quality.py <스킬명> [...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import PLUGINS_DIR, force_utf8_stdout, parse_frontmatter, read_text, skill_dir  # noqa: E402
import validate_skills  # noqa: E402

SKILL_SECTIONS = ["## 언제 쓰는가", "## 시작 전에", "## 워크플로", "## 건너뛰기 쉬운 단계", "## 맞춤", "## 참고"]
README_SECTIONS = ["## 하는 일", "## 데모", "## 요구사항", "## 지원 환경", "## 커스터마이즈 포인트", "## 데이터 흐름", "## 변경 이력"]
PATH_REF = re.compile(r"(?<![\w/])((?:references|scripts|templates)/[\w./-]+\.(?:md|py|json|pptx|yaml))")


def check(skill: str) -> list[str]:
    p: list[str] = []
    d = skill_dir(skill)
    md = d / "SKILL.md"
    if not md.is_file():
        return [f"{skill}: SKILL.md 없음"]
    fm, body, errs = parse_frontmatter(read_text(md))
    p += [f"{skill}: frontmatter {e}" for e in errs]
    if fm.get("name") != skill:
        p.append(f"{skill}: name이 디렉터리명과 다름")
    desc = fm.get("description", "")
    if not (300 <= len(desc) <= 1024):
        p.append(f"{skill}: description {len(desc)}자(300~1024)")
    if "쓰지 않" not in desc:
        p.append(f"{skill}: description에 사용하지 않는 경우(경계)가 없음")
    if not isinstance(fm.get("metadata"), dict) or not fm["metadata"].get("version"):
        p.append(f"{skill}: metadata.version 없음")
    lines = body.splitlines()
    if len(lines) > 500:
        p.append(f"{skill}: 본문 {len(lines)}줄 > 500")
    for sec in SKILL_SECTIONS:
        if not any(l.startswith(sec) for l in lines):
            p.append(f"{skill}: SKILL.md 섹션 없음 '{sec}'")
    if "- [ ]" not in body:
        p.append(f"{skill}: 워크플로 체크리스트 없음")
    # README 커스터마이즈 표에 적힌 경로는 오버라이드 폴더에 두는 파일이라 스킬 폴더에 없어도 된다
    rd_text = read_text(d / "README.md") if (d / "README.md").is_file() else ""
    override_only = set(PATH_REF.findall(rd_text.split("## 커스터마이즈 포인트", 1)[-1].split("\n## ", 1)[0]))
    for ref in sorted(set(PATH_REF.findall(body))):
        if "<" in ref or ref.endswith("/") or ref in override_only:
            continue
        if not (d / ref).exists():
            p.append(f"{skill}: 본문이 언급한 파일 없음 {ref}")
    findings = validate_skills.check_skill(d, PLUGINS_DIR.parent)
    p += [f"{skill}: 정적 검증 {f['severity']} {f['rule']} {f['file']}:{f['line']}" for f in findings]
    rd = d / "README.md"
    if not rd.is_file():
        p.append(f"{skill}: README.md 없음")
    else:
        rt = read_text(rd)
        for sec in README_SECTIONS:
            if sec not in rt:
                p.append(f"{skill}: README 섹션 없음 '{sec}'")
        cust = rt.split("## 커스터마이즈 포인트", 1)[-1].split("\n## ", 1)[0]
        if not re.search(r"^\|\s*L[0-2]\s*\|", cust, re.M):
            p.append(f"{skill}: 커스터마이즈 포인트 표에 L0~L2 행 없음")
    return p


def main(argv: list[str]) -> int:
    force_utf8_stdout()
    if not argv:
        print(__doc__)
        return 2
    problems = [x for s in argv for x in check(s)]
    for x in problems:
        print("FAIL:", x)
    if problems:
        return 1
    print(f"checked: {', '.join(argv)}")
    print("SKILL QUALITY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
