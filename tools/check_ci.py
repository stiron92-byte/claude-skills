#!/usr/bin/env python3
"""G14 오라클: CI 워크플로가 유효한 YAML이고 로컬 검증 명령을 빠짐없이 실행하는지 확인한다.

- .github/workflows/ci.yml 을 PyYAML이 있으면 그것으로, 없으면 constraints로 고정된 venv의 PyYAML로 파싱한다
- 아래 REQUIRED_COMMANDS가 모두 어떤 job의 run 단계에 들어 있다
- 체크아웃이 태그를 가져온다(fetch-depth: 0) — 마이그레이션·baseline 검사에 필요
- static job이 Windows와 Ubuntu 둘 다에서 돈다
- evals job은 수동 실행(workflow_dispatch)으로만 돈다
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ROOT, force_utf8_stdout  # noqa: E402

CI = ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED_COMMANDS = [
    "python tools/validate_skills.py --baseline tools/validate-baseline.json",
    "python tests/control_validator_detects.py",
    "python tools/build.py --check",
    "python tools/compile_all.py",
    'python -m unittest discover -s tests -p "test_*.py"',
    "python tools/check_evals.py",
    "python tools/check_pins.py",
    "python tools/check_pins.py --install",
    "python tools/check_sizes.py",
    "python tools/check_migration.py",
    "python tools/make_baseline.py --verify",
    "python tools/check_docx_slim.py",
    "python tools/check_docs.py",
    "python tools/check_traces.py",
    "python tools/check_doctor.py",
    "python tools/run_plugin_validate.py",
    "claude plugin eval",
    "python tests/check_extract_sources.py",
    "python tests/check_build_deck.py",
    "python tests/check_verify_deck.py",
    "python tests/check_hwpx_editor.py",
    "python tests/check_excel_practice_inputs.py",
    "python tests/check_excel_clean.py",
    "python tests/check_excel_consolidate.py --allow-no-engine",
    "python tests/check_verify_excel.py --allow-no-engine",
    "python tests/check_meeting_practice.py",
    "python tests/check_prepare_transcript.py",
    "python tests/check_build_minutes.py",
    "python tests/check_verify_minutes.py",
    "python tests/check_transcribe.py --allow-missing",
    "python tests/check_repurpose_practice.py",
    "python tests/check_count_chars.py",
    "python tests/check_repurpose_verify.py",
    "python tests/check_content_inventory.py",
    "python tools/check_skill_quality.py doc-automation hwpx-editor excel-automation meeting-minutes content-repurpose",
    "python tools/check_skillcreator_evals.py doc-automation hwpx-editor excel-automation meeting-minutes content-repurpose",
]


def load_yaml(text: str):
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        py = ROOT / ".workspace" / "pins-venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not py.is_file():
            raise SystemExit("FAIL: PyYAML 없음 — python tools/check_pins.py --install 후 다시 실행")
        r = subprocess.run([str(py), "-c", "import json,sys,yaml;print(json.dumps(yaml.safe_load(sys.stdin.read())))"],
                           input=text, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise SystemExit(f"FAIL: YAML 파싱 오류 {r.stderr[-500:]}")
        import json
        return json.loads(r.stdout)


def main() -> int:
    force_utf8_stdout()
    doc = load_yaml(CI.read_text(encoding="utf-8"))
    problems: list[str] = []
    jobs = doc.get("jobs", {})
    runs = []
    for jn, job in jobs.items():
        for st in job.get("steps", []):
            if "run" in st:
                runs.append(" ".join(str(st["run"]).split()))
    joined = "\n".join(runs)
    for c in REQUIRED_COMMANDS:
        if " ".join(c.split()) not in joined:
            problems.append(f"CI에 없는 명령: {c}")
    static = jobs.get("static", {})
    oses = static.get("strategy", {}).get("matrix", {}).get("os", [])
    if not {"ubuntu-latest", "windows-latest"} <= set(oses):
        problems.append(f"static job OS 매트릭스 부족: {oses}")
    co = [s for s in static.get("steps", []) if str(s.get("uses", "")).startswith("actions/checkout")]
    if not co or co[0].get("with", {}).get("fetch-depth") != 0:
        problems.append("static job checkout에 fetch-depth: 0 없음")
    ev = jobs.get("evals", {})
    if "workflow_dispatch" not in str(ev.get("if", "")):
        problems.append("evals job이 수동 실행 조건이 아님")
    # PyYAML은 'on'을 True로 읽는다
    triggers = doc.get("on", doc.get(True, {}))
    if "workflow_dispatch" not in triggers:
        problems.append("workflow_dispatch 트리거 없음")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    print(f"jobs={list(jobs)} run-steps={len(runs)}")
    print("CI OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
