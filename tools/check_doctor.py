#!/usr/bin/env python3
"""G11 오라클: 실습 플러그인의 doctor(vendoring된 사본)가 이 PC에서 실제로 동작하는지 확인한다.

- doctor 스킬 폴더의 scripts/_vendor/doctor.py 를 --json 으로 실행한다
- 8개 업무·크리에이터 스킬 모두에 대한 준비 상태가 나온다
- ok가 아닌 모든 항목에 해결 명령이 있다
- counts 합계가 checks 수와 같다
- --strict 종료 코드가 fail 개수와 일치한다(fail>0이면 1, 아니면 0)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import LEGACY_SKILLS, force_utf8_stdout, skill_dir  # noqa: E402

DOCTOR = skill_dir("doctor") / "scripts" / "_vendor" / "doctor.py"


def main() -> int:
    force_utf8_stdout()
    problems: list[str] = []
    r = subprocess.run([sys.executable, str(DOCTOR), "--json"], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("FAIL: doctor 실행 실패", r.stderr[-800:])
        return 1
    rep = json.loads(r.stdout)
    if set(rep["skills"]) != set(LEGACY_SKILLS):
        problems.append(f"스킬 목록 불일치: {sorted(rep['skills'])}")
    if sum(rep["counts"].values()) != len(rep["checks"]):
        problems.append("counts 합계와 checks 수 불일치")
    for c in rep["checks"]:
        if c["status"] not in ("ok", "warn", "fail"):
            problems.append(f"잘못된 status: {c}")
        if c["status"] != "ok" and not c.get("fix"):
            problems.append(f"해결 명령 없음: {c['id']}")
    if not rep["environment"].get("surface"):
        problems.append("환경 판정 없음")
    s = subprocess.run([sys.executable, str(DOCTOR), "--strict"], capture_output=True, text=True, encoding="utf-8")
    expected = 1 if rep["counts"]["fail"] else 0
    if s.returncode != expected:
        problems.append(f"--strict 종료 코드 {s.returncode} != 기대 {expected}")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    c = rep["counts"]
    print(f"surface={rep['environment']['surface']} os={rep['environment']['os']} ok={c['ok']} warn={c['warn']} fail={c['fail']}")
    print("skills:", json.dumps(rep["skills"], ensure_ascii=False))
    print("DOCTOR OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
