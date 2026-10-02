#!/usr/bin/env python3
"""G5 양성 대조군: 정적 검증기가 '새로 들어온' 위반을 실제로 잡는지 확인한다.

baseline 방식은 기존 위반을 허용하므로, 검증기가 고장 나도 'VALIDATE OK'가 나올 수 있다.
그래서 임시 트리에 깨끗한 스킬을 복사한 뒤
  (a) 수정 없이 검사 → 통과해야 한다(음성 대조)
  (b) 금지 경로·이름 불일치·깨진 링크·비밀값을 주입 → 각각 새 error로 잡혀야 한다(양성 대조)
를 확인하고, 실제 저장소 baseline을 써도 주입한 위반이 허용되지 않는지 본다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_skills.py"
BASELINE = ROOT / "tools" / "validate-baseline.json"
CLEAN_SKILL = ROOT / "plugins" / "kevin-skills-practice" / "skills" / "doctor"


def run(root: Path) -> dict:
    r = subprocess.run([sys.executable, str(VALIDATOR), "--root", str(root), "--baseline", str(BASELINE), "--json"],
                       capture_output=True, text=True, encoding="utf-8")
    data = json.loads(r.stdout[: r.stdout.rindex("}") + 1])
    data["exit"] = r.returncode
    return data


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    with tempfile.TemporaryDirectory() as td:
        plugins = Path(td) / "plugins"
        dst = plugins / "p" / "skills" / "doctor"
        shutil.copytree(CLEAN_SKILL, dst)

        clean = run(plugins)
        if clean["exit"] != 0 or clean["summary"]["new_errors"] != 0:
            print("FAIL: 깨끗한 스킬이 통과하지 못함", clean["summary"])
            return 1

        md = dst / "SKILL.md"
        text = md.read_text(encoding="utf-8")
        text = text.replace("name: doctor", "name: doctor-renamed")
        text += "\n결과는 /mnt/user-data/outputs/ 에 저장하고 present_files로 보여 준다.\n"
        text += "\n[없는 파일](references/nope.md)\n"
        md.write_text(text, encoding="utf-8")
        (dst / "references").mkdir(exist_ok=True)
        (dst / "references" / "conf.yaml").write_text('api_key: "abcd1234efgh5678ijkl"\n', encoding="utf-8")
        (dst / "references" / "conf.md").write_text("경로: /Users/someone/Desktop/a.docx\n", encoding="utf-8")

        dirty = run(plugins)
        rules = {f["rule"] for f in dirty["new"] if f["severity"] == "error"}
        expected = {"name", "env-path", "broken-link", "secret", "personal-path"}
        missing = expected - rules
        if dirty["exit"] != 1 or missing:
            print("FAIL: 주입한 위반을 놓침", {"exit": dirty["exit"], "missing": sorted(missing), "got": sorted(rules)})
            return 1
    print(f"clean exit=0, injected exit=1, detected rules={sorted(rules)}")
    print("CONTROL DETECTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
