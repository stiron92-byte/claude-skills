#!/usr/bin/env python3
"""실습 샘플을 작업 폴더로 복사한다.

샘플은 플러그인 설치 폴더 안에 있어 사용자가 찾기 어렵고, 그 자리에서 수정하면 업데이트 때 사라진다.
그래서 항상 사용자의 작업 폴더로 복사해서 쓴다. 이미 있는 파일은 덮어쓰지 않는다.

사용법
  python copy_samples.py --list                       # 세트 목록
  python copy_samples.py --list --chapter 2
  python copy_samples.py --set doc-company-ppt        # 현재 폴더 아래 '2장-기업PPT/'로 복사
  python copy_samples.py --set doc-fx-pdf --dest D:/실습
  python copy_samples.py --chapter 4                  # 4장 입력 세트 전부
  python copy_samples.py --verify                     # catalog의 모든 파일이 실제로 있는지 검사
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
CATALOG = SAMPLES / "catalog.json"


def load() -> list[dict]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))["sets"]


def expand(pattern: str) -> list[Path]:
    if any(ch in pattern for ch in "*?["):
        return sorted(p for p in SAMPLES.glob(pattern) if p.is_file())
    p = SAMPLES / pattern
    return [p] if p.is_file() else []


def copy_set(s: dict, dest_root: Path) -> dict:
    target = dest_root / s["folder"]
    target.mkdir(parents=True, exist_ok=True)
    copied, skipped, missing = [], [], []
    for pat in s["files"]:
        files = expand(pat)
        if not files:
            missing.append(pat)
        for f in files:
            out = target / f.name
            if out.exists():
                skipped.append(str(out))  # 사용자가 이미 고친 파일일 수 있으므로 덮어쓰지 않는다
            else:
                shutil.copy2(f, out)
                copied.append(str(out))
    return {"set": s["id"], "dest": str(target), "copied": copied, "skipped_existing": skipped, "missing": missing}


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="실습 샘플 복사")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--skill")
    ap.add_argument("--include-results", action="store_true", help="완성 예시(reference-output)도 함께 복사")
    ap.add_argument("--dest", default=".")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    sets = load()

    if a.verify:
        problems = [f"{s['id']}: {pat}" for s in sets for pat in s["files"] if not expand(pat)]
        ids = [s["id"] for s in sets]
        problems += [f"중복 id: {i}" for i in set(ids) if ids.count(i) > 1]
        for p in problems:
            print("MISSING:", p)
        print("CATALOG OK" if not problems else "CATALOG INVALID")
        return 0 if not problems else 1

    chosen = [s for s in sets if
              (not a.chapter or s["chapter"] == a.chapter) and (not a.skill or s["skill"] == a.skill)]
    if a.list or not (a.set or a.chapter or a.skill):
        for s in chosen:
            n = sum(len(expand(p)) for p in s["files"])
            print(f"{s['id']:<26} {s['chapter']:>2}장  {s['kind']:<16} 파일 {n:>2}개  {s['title']}")
        return 0

    if a.set:
        unknown = [x for x in a.set if x not in {s["id"] for s in sets}]
        if unknown:
            print("알 수 없는 세트:", ", ".join(unknown), "→ --list로 확인하세요")
            return 2
        chosen = [s for s in sets if s["id"] in a.set]
    elif not a.include_results:
        chosen = [s for s in chosen if s["kind"] != "reference-output"]

    dest = Path(a.dest).resolve()
    results = [copy_set(s, dest) for s in chosen]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    for s in chosen:
        if s.get("rights"):
            print(f"\n[주의] {s['id']}: {s['rights']}")
        if s.get("note"):
            print(f"\n[참고] {s['id']}: {s['note']}")
    return 1 if any(r["missing"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
