#!/usr/bin/env python3
"""G2 오라클: v1.6.1의 skills/ 아래 모든 파일이 새 위치에 손실 없이 옮겨졌는지 검증한다.

각 v1.6.1 파일은 다음 중 하나여야 한다.
- 새 스킬 폴더의 같은 상대 경로에 바이트 동일하게 존재
- 실습 플러그인 samples/ 로 이동(assets/·samples/ 하위) 하고 바이트 동일
- 의도적으로 수정됨(INTENDED_EDITS) — 파일은 존재해야 한다
- 의도적으로 삭제·이동됨(INTENDED_REMOVALS) — 사유가 기록되어 있어야 한다
목록에 없는 차이는 모두 실패다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import BASELINE_TAG, LEGACY_SKILLS, ROOT, force_utf8_stdout, git, skill_dir  # noqa: E402

SAMPLES = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples"

INTENDED_REMOVALS = {
    "skills/doc-automation/scripts/fix_captions.py": "작성자 로컬 경로 하드코딩된 원고 교정용 1회성 스크립트",
    "skills/doc-automation/scripts/fix_docx.py": "작성자 로컬 경로 하드코딩된 원고 교정용 1회성 스크립트",
    "skills/doc-automation/scripts/fix_docx_round2.py": "작성자 로컬 경로 하드코딩된 원고 교정용 1회성 스크립트",
    "skills/doc-automation/scripts/make_fireworks_report.py": "작성자 로컬 경로 하드코딩된 1회성 보고서 생성 스크립트",
    "skills/doc-automation/scripts/create_sample_templates.py": "tools/dev/create_sample_templates.py 로 이동(개발용)",
}
# Phase 1 이동(옛 경로 → 새 경로, 새 경로에 반드시 있어야 함). modified=True면 내용 변경 허용
INTENDED_MOVES = {
    "skills/doc-automation/scripts/hwpx_template.py": ("plugins/kevin-skills-book/skills/hwpx-editor/scripts/hwpx_template.py", True),
    "skills/doc-automation/scripts/hwpx_parser.py": ("shared/optional/hwpx_parser.py", True),  # 배포용(암호화) 문서 감지 추가
}
# 현재 경로 기준
INTENDED_EDITS = {
    "plugins/kevin-skills-book/skills/doc-automation/SKILL.md": "샘플 위치를 실습 플러그인으로 안내",
    "plugins/kevin-skills-book/skills/meeting-minutes/SKILL.md": "샘플 위치를 실습 플러그인으로 안내",
    "plugins/kevin-skills-book/skills/doc-automation/scripts/generate_report.py": "사용 예시의 samples/ 경로 제거",
    "plugins/kevin-skills-book/skills/doc-automation/scripts/requirements.txt": "의존성 == 고정(tools/check_pins.py가 검증)",
    "plugins/kevin-skills-book/skills/data-collector/scripts/requirements.txt": "의존성 == 고정(tools/check_pins.py가 검증)",
    "plugins/kevin-skills-creator/skills/content-research/scripts/requirements.txt": "의존성 == 고정(tools/check_pins.py가 검증)",
    "plugins/kevin-skills-practice/skills/practice-samples/samples/excel-automation/prompt/2.md":
        "v1.6.1에서 빈 파일이었다. 스킬 사용 실습 프롬프트로 채움(tests/check_excel_practice_inputs.py가 검증)",
}
SLIMMED_DOCX_DIR = "doc-automation/example/example_3_comany-to-ppt/"  # 내장 글꼴 제거(G12가 별도 검증)
# Phase 1에서 재설계한 스킬: 파일이 남아 있으면 내용 변경을 허용한다(품질은 각 스킬의 Phase 1 gate가 검증)
PHASE1_REWRITTEN = {"doc-automation", "excel-automation", "meeting-minutes", "content-repurpose"}


def new_location(old: str) -> Path | None:
    parts = old.split("/")
    skill, rest = parts[1], "/".join(parts[2:])
    if skill not in LEGACY_SKILLS:
        return None
    if rest.startswith("assets/"):
        return SAMPLES / skill / rest[len("assets/"):]
    if skill == "doc-automation" and rest.startswith("samples/"):
        return SAMPLES / "doc-automation" / rest
    return skill_dir(skill) / rest


def main() -> int:
    force_utf8_stdout()
    # 파일 비교는 git blob 해시로 한다. Windows의 core.autocrlf가 작업 트리 줄바꿈을 CRLF로 바꾸므로
    # 바이트 비교는 내용이 같아도 실패한다. hash-object는 같은 변환을 되돌린 뒤 해시한다.
    old_blobs = {}
    for line in git("ls-tree", "-r", BASELINE_TAG, "skills").splitlines():
        meta, path = line.split("	", 1)
        old_blobs[path] = meta.split()[2]
    old_files = sorted(old_blobs)
    problems: list[str] = []
    stats = {"identical": 0, "edited": 0, "slimmed": 0, "removed": 0}
    for old in old_files:
        if old in INTENDED_REMOVALS:
            if (ROOT / "plugins").joinpath(*old.split("/")[1:]).exists():
                problems.append(f"삭제 예정인데 남아 있음: {old}")
            stats["removed"] += 1
            continue
        if old in INTENDED_MOVES:
            target, modified = INTENDED_MOVES[old]
            tp = ROOT / target
            if not tp.is_file():
                problems.append(f"이동 대상 없음: {old} → {target}")
            elif not modified and git("hash-object", str(tp)).strip() != old_blobs[old]:
                problems.append(f"이동 후 내용 변경(의도 목록에 없음): {target}")
            stats["edited" if modified else "identical"] += 1
            continue
        new = new_location(old)
        if new is None:
            problems.append(f"알 수 없는 스킬: {old}")
            continue
        if not new.is_file():
            problems.append(f"누락: {old} → {new.relative_to(ROOT)}")
            continue
        rel_new = new.relative_to(ROOT).as_posix()
        if rel_new in INTENDED_EDITS or (old.split("/")[1] in PHASE1_REWRITTEN and not rel_new.startswith(
                "plugins/kevin-skills-practice/") and git("hash-object", str(new)).strip() != old_blobs[old]):
            stats["edited"] += 1
            continue
        if SLIMMED_DOCX_DIR in rel_new and new.suffix == ".docx":
            stats["slimmed"] += 1
            continue
        if git("hash-object", str(new)).strip() != old_blobs[old]:
            problems.append(f"내용 변경(의도 목록에 없음): {rel_new}")
            continue
        stats["identical"] += 1
    for skill in LEGACY_SKILLS:
        if not (skill_dir(skill) / "SKILL.md").is_file():
            problems.append(f"SKILL.md 없음: {skill}")
    if (ROOT / "skills").exists():
        problems.append("구 skills/ 폴더가 남아 있음")
    print(f"v1.6.1 files: {len(old_files)}  {stats}")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("MIGRATION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
