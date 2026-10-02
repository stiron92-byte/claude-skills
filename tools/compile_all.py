#!/usr/bin/env python3
"""G7 오라클: 저장소의 모든 배포·도구 Python 파일이 현재 Python으로 컴파일되는지 확인한다.

내장 compile()을 써서 .pyc 파일을 만들지 않는다. chapter*/ 폴더(책 스냅샷)는 범위 밖이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ROOT, force_utf8_stdout  # noqa: E402

DIRS = ["plugins", "shared", "tools", "tests"]


def main() -> int:
    force_utf8_stdout()
    files = sorted(p for d in DIRS for p in (ROOT / d).rglob("*.py") if "__pycache__" not in p.parts)
    bad = []
    for p in files:
        try:
            compile(p.read_bytes(), str(p), "exec", dont_inherit=True)
        except SyntaxError as e:
            bad.append(f"{p.relative_to(ROOT)}:{e.lineno} {e.msg}")
    if not files:
        print("FAIL: Python 파일을 찾지 못함")
        return 1
    for b in bad:
        print("FAIL:", b)
    if bad:
        return 1
    print(f"compiled {len(files)} files with Python {sys.version.split()[0]}")
    print("COMPILE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
