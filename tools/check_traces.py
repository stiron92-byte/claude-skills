#!/usr/bin/env python3
"""G17 오라클: 작업 트리에 원 저장소 소유자 흔적(계정명·로컬 경로·이메일)이 없는지 확인한다.

- 검사 대상: .git, .workspace 를 제외한 모든 파일. 텍스트는 그대로, docx/pptx/xlsx/hwpx는 내부 XML까지 본다.
- 검색어는 이 파일 자체가 걸리지 않도록 뒤집힌 문자열로 보관한다.
- 양성 대조: 임시 파일에 검색어를 넣어 실제로 잡히는지 먼저 확인한다. 못 잡으면 실패.
- 커밋 이력·GitHub fork 연결은 작업 트리 밖이므로 이 검사 범위가 아니다(계획서 §7.1).
"""
from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ROOT, force_utf8_stdout  # noqa: E402

TOKENS = [t[::-1] for t in ("etyb-29noits", "1060ejad", "losadgnag", "8114tmhsilgne")]
SKIP_DIRS = {".git", ".workspace", "__pycache__", ".unlazy"}
ZIP_EXT = {".docx", ".pptx", ".xlsx", ".hwpx"}


def scan_file(p: Path) -> list[str]:
    hits = []
    try:
        if p.suffix.lower() in ZIP_EXT:
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.endswith((".xml", ".rels", ".hpf")):
                        low = z.read(n).decode("utf-8", "ignore").lower()
                        hits += [f"{n}:{t}" for t in TOKENS if t in low]
        else:
            low = p.read_bytes().decode("utf-8", "ignore").lower()
            hits += [t for t in TOKENS if t in low]
    except (zipfile.BadZipFile, OSError):
        pass
    return hits


def walk(root: Path):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            yield Path(dp) / f


def main() -> int:
    force_utf8_stdout()
    with tempfile.TemporaryDirectory() as td:
        ctl = Path(td) / "control.md"
        ctl.write_text(f"owner: {TOKENS[0].upper()}\n", encoding="utf-8")
        if not scan_file(ctl):
            print("FAIL: 양성 대조군을 잡지 못함(검사기 고장)")
            return 1
    found = {}
    n = 0
    for p in walk(ROOT):
        n += 1
        h = scan_file(p)
        if h:
            found[p.relative_to(ROOT).as_posix()] = h
    for f, h in found.items():
        print("FAIL:", f, h)
    if found:
        return 1
    print(f"control detected; scanned {n} files")
    print("TRACES CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
