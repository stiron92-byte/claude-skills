#!/usr/bin/env python3
"""G16 오라클: 공통 규약 문서와 템플릿이 필수 섹션을 갖추었는지, 코드와 문서가 서로 맞는지 확인한다.

- shared/references/environment.md, overrides.md: 필수 섹션
- overrides.md의 보호 규칙 id 목록 == shared/scripts/overrides.py PROTECTED_RULES id 목록
- overrides.md의 오버라이드 폴더 경로 == overrides.py OVERRIDE_DIRNAME
- docs/templates/SKILL.template.md: frontmatter 자리와 필수 섹션
- docs/templates/README.template.md: 필수 섹션(커스터마이즈 포인트 포함)
- 실습 스킬 2개의 SKILL.md가 참조하는 스크립트가 실제로 있다
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ROOT, SHARED_DIR, force_utf8_stdout, read_text, skill_dir  # noqa: E402

sys.path.insert(0, str(SHARED_DIR / "scripts"))
import overrides  # noqa: E402

REQ = {
    SHARED_DIR / "references" / "environment.md": ["## 1.", "## 2. 입력 파일", "## 3. 출력 위치", "## 4. 결과 전달",
                                                    "## 5. 다른 스킬 참조", "## 6. 명령 시간 제한", "## 7. 운영체제 차이"],
    SHARED_DIR / "references" / "overrides.md": ["## 1. 맞춤 수준", "## 2. 오버라이드 폴더와 탐색 순서", "## 3. 스킬이 해야 할 일",
                                                  "## 4. settings 파일", "## 5. 보호 규칙", "## 6. 공유 전 검사"],
    ROOT / "docs" / "templates" / "SKILL.template.md": ["name:", "description:", "metadata:", "## 언제 쓰는가",
                                                        "## 시작 전에", "## 워크플로", "## 출력 규격", "## 품질 게이트",
                                                        "## 건너뛰기 쉬운 단계", "## 맞춤(오버라이드)", "## 참고"],
    ROOT / "docs" / "templates" / "README.template.md": ["## 하는 일", "## 데모", "## 요구사항", "## 지원 환경",
                                                         "## 커스터마이즈 포인트", "## 데이터 흐름", "## 변경 이력"],
}


def main() -> int:
    force_utf8_stdout()
    problems: list[str] = []
    for path, needles in REQ.items():
        if not path.is_file():
            problems.append(f"없음: {path.relative_to(ROOT)}")
            continue
        text = read_text(path)
        for n in needles:
            if n not in text:
                problems.append(f"{path.relative_to(ROOT)}: '{n}' 섹션 없음")
    ov = read_text(SHARED_DIR / "references" / "overrides.md")
    doc_ids = set(re.findall(r"^\|\s*([a-z][a-z0-9-]+)\s*\|", ov.split("## 5.")[1].split("## 6.")[0], re.M)) - {"id"}
    code_ids = {r["id"] for r in overrides.PROTECTED_RULES}
    if doc_ids != code_ids:
        problems.append(f"보호 규칙 불일치 문서={sorted(doc_ids)} 코드={sorted(code_ids)}")
    if overrides.OVERRIDE_DIRNAME.as_posix() not in ov:
        problems.append(f"overrides.md에 폴더 경로 {overrides.OVERRIDE_DIRNAME.as_posix()} 없음")
    for skill, script in (("practice-samples", "scripts/copy_samples.py"), ("doctor", "scripts/_vendor/doctor.py")):
        md = read_text(skill_dir(skill) / "SKILL.md")
        if script not in md:
            problems.append(f"{skill}/SKILL.md가 {script}를 안내하지 않음")
        if not (skill_dir(skill) / script).is_file():
            problems.append(f"{skill}: {script} 없음")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    print(f"protected rules={len(code_ids)} documents={len(REQ)}")
    print("DOCS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
