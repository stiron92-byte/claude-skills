#!/usr/bin/env python3
"""Phase 0 검증 명령 전체를 한 번에 실행하는 회귀 검사(Phase 1 이후 매 스킬 작업마다 실행).

각 명령의 성공 표식(마지막 줄 근처)이 나와야 통과로 본다. 하나라도 실패하면 exit 1.
claude CLI가 필요한 run_plugin_validate도 포함한다. pins --install(수 분 소요)은 제외하고 CI에 맡긴다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    (["tools/run_plugin_validate.py"], "PLUGIN VALIDATE OK"),
    (["tools/build.py", "--check"], "VENDOR IN SYNC"),
    (["tools/validate_skills.py", "--baseline", "tools/validate-baseline.json"], "VALIDATE OK"),
    (["tests/control_validator_detects.py"], "CONTROL DETECTED"),
    (["tools/compile_all.py"], "COMPILE OK"),
    (["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], "OK"),
    (["tools/check_evals.py"], "EVALS OK"),
    (["tools/check_pins.py"], "PINS OK"),
    (["tools/check_docs.py"], "DOCS OK"),
    (["tools/check_sizes.py"], "SIZES OK"),
    (["tools/check_migration.py"], "MIGRATION OK"),
    (["tools/check_traces.py"], "TRACES CLEAN"),
    (["tools/check_doctor.py"], "DOCTOR OK"),
    (["tools/make_baseline.py", "--verify"], "BASELINE OK"),
    (["tools/check_ci.py"], "CI OK"),
    # Phase 1에서 고도화를 마친 스킬
    (["tests/check_extract_sources.py"], "EXTRACT OK"),
    (["tests/check_build_deck.py"], "BUILD DECK OK"),
    (["tests/check_verify_deck.py"], "VERIFY DECK CONTROL OK"),
    (["tests/check_hwpx_editor.py"], "HWPX EDITOR OK"),
    (["tests/check_excel_practice_inputs.py"], "PRACTICE INPUTS OK"),
    (["tests/check_excel_clean.py"], "EXCEL CLEAN OK"),
    (["tests/check_excel_consolidate.py", "--allow-no-engine"], "EXCEL CONSOLIDATE"),
    (["tests/check_verify_excel.py", "--allow-no-engine"], "VERIFY EXCEL CONTROL OK"),
    (["tests/check_meeting_practice.py"], "MEETING PRACTICE OK"),
    (["tests/check_prepare_transcript.py"], "PREPARE TRANSCRIPT OK"),
    (["tests/check_build_minutes.py"], "BUILD MINUTES OK"),
    (["tests/check_verify_minutes.py"], "VERIFY MINUTES CONTROL OK"),
    (["tests/check_transcribe.py"], "TRANSCRIBE OK"),
    (["tests/check_repurpose_practice.py"], "REPURPOSE PRACTICE OK"),
    (["tests/check_count_chars.py"], "COUNT CHARS OK"),
    (["tests/check_repurpose_verify.py"], "REPURPOSE VERIFY CONTROL OK"),
    (["tests/check_content_inventory.py"], "CONTENT INVENTORY OK"),
    (["tools/check_skill_quality.py", "doc-automation", "hwpx-editor", "excel-automation", "meeting-minutes", "content-repurpose"], "SKILL QUALITY OK"),
    (["tools/check_skillcreator_evals.py", "doc-automation", "hwpx-editor", "excel-automation", "meeting-minutes", "content-repurpose"], "SKILLCREATOR EVALS OK"),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    failed = []
    for args, marker in CHECKS:
        r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        out = (r.stdout + r.stderr).strip()
        tail = out.splitlines()[-3:] if out else []
        ok = r.returncode == 0 and any(marker in line for line in tail)
        print(f"{'PASS' if ok else 'FAIL'}  {' '.join(args)}")
        if not ok:
            failed.append(" ".join(args))
            print("      " + "\n      ".join(out.splitlines()[-8:]))
    if failed:
        print(f"REGRESSION FAILED: {len(failed)}")
        return 1
    print(f"{len(CHECKS)} checks passed")
    print("REGRESSION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
