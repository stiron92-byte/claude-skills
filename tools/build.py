#!/usr/bin/env python3
"""shared/ 공통 모듈을 각 스킬에 복사(vendoring)한다.

왜 복사하나: 스킬은 플러그인 설치 외에도 '스킬 폴더만 복사'(수동 설치)나
claude.ai 스킬 단위 업로드로 배포된다. 이때 스킬 밖의 shared/는 따라가지 않으므로
각 스킬이 자기 폴더 안에 사본을 가져야 한다. 원본은 shared/ 하나뿐이다.

  shared/scripts/*.py      → <스킬>/scripts/_vendor/
  shared/references/*.md   → <스킬>/references/_shared/

사본은 직접 고치지 않는다. shared/를 고친 뒤 이 스크립트를 다시 실행한다.

사용법
  python tools/build.py           # 복사(남는 오래된 사본은 삭제)
  python tools/build.py --check   # 사본이 원본과 같은지만 검사(CI용)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import OPTIONAL_VENDOR, SHARED_DIR, VENDOR_TARGETS, force_utf8_stdout, skill_dir  # noqa: E402

README = (
    "# 자동 생성 폴더 — 직접 수정하지 마세요\n\n"
    "이 폴더는 저장소 루트의 `shared/`에서 `tools/build.py`가 복사한 사본입니다.\n"
    "수정은 `shared/`에서 하고 `python tools/build.py`를 다시 실행하세요.\n"
)

MAPPING = [
    (SHARED_DIR / "scripts", "*.py", Path("scripts") / "_vendor"),
    (SHARED_DIR / "references", "*.md", Path("references") / "_shared"),
]


def expected_files() -> dict[Path, bytes]:
    out: dict[Path, bytes] = {}
    for skill in VENDOR_TARGETS:
        base = skill_dir(skill)
        if not base.is_dir():
            raise SystemExit(f"스킬 폴더가 없습니다: {base}")
        for src_dir, pattern, rel in MAPPING:
            sources = sorted(src_dir.glob(pattern))
            if not sources:
                raise SystemExit(f"원본이 비어 있습니다: {src_dir}/{pattern}")
            for src in sources:
                out[base / rel / src.name] = src.read_bytes()
            out[base / rel / "README.md"] = README.encode("utf-8")
    for fname, skills in OPTIONAL_VENDOR.items():
        src = SHARED_DIR / "optional" / fname
        if not src.is_file():
            raise SystemExit(f"선택 공통 모듈이 없습니다: {src}")
        for skill in skills:
            out[skill_dir(skill) / "scripts" / "_vendor" / fname] = src.read_bytes()
    return out


def existing_vendor_files() -> set[Path]:
    found: set[Path] = set()
    for skill in VENDOR_TARGETS:
        base = skill_dir(skill)
        for _, _, rel in MAPPING:
            d = base / rel
            if d.is_dir():
                found.update(p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return found


def _norm(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def main(argv: list[str]) -> int:
    force_utf8_stdout()
    exp = expected_files()
    existing = existing_vendor_files()
    if "--check" in argv:
        problems = []
        for p, data in exp.items():
            if not p.is_file():
                problems.append(f"없음: {p}")
            elif _norm(p.read_bytes()) != _norm(data):  # Windows checkout(core.autocrlf)은 줄 끝만 CRLF로 바꾼다
                problems.append(f"원본과 다름: {p}")
        for p in sorted(existing - set(exp)):
            problems.append(f"원본에 없는 사본: {p}")
        if problems:
            for x in problems:
                print("FAIL:", x)
            print("→ python tools/build.py 를 실행해 동기화하세요.")
            return 1
        print(f"{len(exp)} vendored files across {len(VENDOR_TARGETS)} skills")
        print("VENDOR IN SYNC")
        return 0
    written = 0
    for p, data in exp.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.is_file() or p.read_bytes() != data:
            p.write_bytes(data)
            written += 1
    removed = 0
    for p in sorted(existing - set(exp)):
        p.unlink()
        removed += 1
    print(f"written {written}, removed {removed}, total {len(exp)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
