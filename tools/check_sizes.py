#!/usr/bin/env python3
"""G13 오라클: 플러그인별 설치 크기와 샘플 바이너리 포함 여부를 측정한다.

- 업무 플러그인(kevin-skills-book): 1MB 이하, 샘플 바이너리 없음
- 크리에이터 플러그인: 1MB 이하, 샘플 바이너리 없음
- 실습 플러그인: 샘플이 있는 것이 정상, 회귀 감시용 상한 6MB
샘플 바이너리: pptx, docx, hwpx, xlsx, pdf, mp3, wav, m4a, mp4, png, jpg
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import PLUGINS_DIR, force_utf8_stdout  # noqa: E402

BINARY_EXT = {".pptx", ".docx", ".hwpx", ".xlsx", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".png", ".jpg", ".jpeg"}
LIMITS = {"kevin-skills-book": 1_000_000, "kevin-skills-creator": 1_000_000, "kevin-skills-practice": 6_000_000}  # 회의 녹음 mp3 2.2MB·로고 png 1MB 포함, 회귀 감시용 상한
NO_BINARIES = {"kevin-skills-book", "kevin-skills-creator"}


def files_of(plugin: Path) -> list[Path]:
    return [p for p in plugin.rglob("*") if p.is_file()
            and "__pycache__" not in p.parts and "results" not in p.relative_to(plugin).parts[:2]]


def main() -> int:
    force_utf8_stdout()
    problems: list[str] = []
    for name, limit in LIMITS.items():
        files = files_of(PLUGINS_DIR / name)
        size = sum(p.stat().st_size for p in files)
        bins = [p.relative_to(PLUGINS_DIR).as_posix() for p in files if p.suffix.lower() in BINARY_EXT]
        print(f"{name:<24} {size / 1024:8.1f} KB  files={len(files)}  binaries={len(bins)}")
        if size > limit:
            problems.append(f"{name}: {size} bytes > {limit}")
        if name in NO_BINARIES and bins:
            problems.append(f"{name}: 샘플 바이너리 포함 {bins[:5]}")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    print("SIZES OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
