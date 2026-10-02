#!/usr/bin/env python3
"""G1 오라클: 공식 `claude plugin validate --strict`를 마켓플레이스, 각 플러그인, 각 skills 폴더에 실행한다.

추가로 마켓플레이스 항목과 plugin.json의 name·version 일치, 플러그인 구성이 tools/_lib.py의
PLUGIN_LAYOUT과 같은지 확인한다. claude CLI가 없으면 실패한다(검증을 건너뛴 것을 통과로 보지 않는다).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import PLUGIN_LAYOUT, PLUGINS_DIR, ROOT, force_utf8_stdout, load_json  # noqa: E402


def run_validate(target: Path) -> tuple[bool, str]:
    # Windows에서는 npm이 만든 확장자 없는 셸 스크립트 'claude'가 먼저 잡혀 실행되지 않는다.
    exe = next((x for x in (shutil.which(n) for n in ("claude.exe", "claude.cmd", "claude")) if x), None)
    if not exe:
        return False, "claude CLI를 찾을 수 없음"
    r = subprocess.run([exe, "plugin", "validate", "--strict", str(target)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    out = (r.stdout + r.stderr).strip()
    return r.returncode == 0 and "Validation passed" in out, out


def main() -> int:
    force_utf8_stdout()
    problems: list[str] = []
    targets = [ROOT / ".claude-plugin" / "marketplace.json"]
    for name in PLUGIN_LAYOUT:
        targets += [PLUGINS_DIR / name, PLUGINS_DIR / name / "skills"]
    for t in targets:
        ok, out = run_validate(t)
        print(f"{'PASS' if ok else 'FAIL'}  {t.relative_to(ROOT)}")
        if not ok:
            problems.append(f"{t}: {out[-600:]}")

    market = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    entries = {e["name"]: e for e in market["plugins"]}
    if set(entries) != set(PLUGIN_LAYOUT):
        problems.append(f"마켓플레이스 플러그인 목록 {sorted(entries)} != {sorted(PLUGIN_LAYOUT)}")
    if market.get("owner", {}).get("name") != "humanist96":
        problems.append("marketplace owner가 humanist96이 아님")
    for name, skills in PLUGIN_LAYOUT.items():
        mf = load_json(PLUGINS_DIR / name / ".claude-plugin" / "plugin.json")
        e = entries.get(name, {})
        if mf.get("name") != name:
            problems.append(f"{name}: plugin.json name 불일치")
        if e.get("source") != f"./plugins/{name}":
            problems.append(f"{name}: source가 ./plugins/{name} 이 아님")
        if e.get("version") != mf.get("version"):
            problems.append(f"{name}: marketplace version {e.get('version')} != plugin.json {mf.get('version')}")
        for k in ("version", "description", "author"):
            if not mf.get(k):
                problems.append(f"{name}: plugin.json {k} 없음")
        actual = sorted(p.name for p in (PLUGINS_DIR / name / "skills").iterdir() if (p / "SKILL.md").is_file())
        if actual != sorted(skills):
            problems.append(f"{name}: 스킬 {actual} != 기대 {sorted(skills)}")
        if (PLUGINS_DIR / name / "CLAUDE.md").exists() or (PLUGINS_DIR / name / "bin").exists():
            problems.append(f"{name}: CLAUDE.md 또는 bin/ 이 있음(로드되지 않거나 Cowork 설치 거부)")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PLUGIN VALIDATE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
