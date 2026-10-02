"""tools/ 스크립트 공용 헬퍼. 표준 라이브러리만 사용한다."""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"
SHARED_DIR = ROOT / "shared"
BASELINE_TAG = "v1.6.1"

# 플러그인 구성(계획서 §7.3). 스킬 → 플러그인 매핑의 단일 출처.
PLUGIN_LAYOUT: dict[str, list[str]] = {
    "kevin-skills-book": ["doc-automation", "hwpx-editor", "excel-automation", "meeting-minutes", "data-collector"],
    "kevin-skills-creator": ["content-research", "content-repurpose", "generate-shorts", "narration-video"],
    "kevin-skills-practice": ["practice-samples", "doctor"],
}
# 업무·크리에이터 스킬(실습 플러그인 제외). v1.6.1의 8개 + Phase 1에서 분리한 hwpx-editor
LEGACY_SKILLS = PLUGIN_LAYOUT["kevin-skills-book"] + PLUGIN_LAYOUT["kevin-skills-creator"]
# 특정 스킬에만 복사하는 선택 공통 모듈: shared/optional/<파일> → <스킬>/scripts/_vendor/
OPTIONAL_VENDOR: dict[str, list[str]] = {
    "hwpx_parser.py": ["doc-automation", "hwpx-editor"],
}
# shared 모듈을 vendoring 받는 스킬
VENDOR_TARGETS = LEGACY_SKILLS + ["doctor"]


def skill_dir(skill: str) -> Path:
    for plugin, skills in PLUGIN_LAYOUT.items():
        if skill in skills:
            return PLUGINS_DIR / plugin / "skills" / skill
    raise KeyError(skill)


def all_skill_dirs() -> list[Path]:
    return [skill_dir(s) for skills in PLUGIN_LAYOUT.values() for s in skills]


def git(*args: str, binary: bool = False):
    r = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout if binary else r.stdout.decode("utf-8")


def parse_frontmatter(text: str) -> tuple[dict, str, list[str]]:
    """간이 YAML frontmatter 파서. (필드, 본문, 오류목록)을 돌려준다.

    PyYAML 없이 동작해야 하므로 스킬 frontmatter에서 쓰는 형태만 지원한다:
    key: value / key: "quoted" / key: >(folded) 또는 |(literal) 다음 들여쓴 줄 /
    key: 다음 들여쓴 하위 맵(metadata 등).
    """
    errors: list[str] = []
    if not text.startswith("---"):
        return {}, text, ["frontmatter가 '---'로 시작하지 않음"]
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not m:
        return {}, text, ["frontmatter 종료 '---'가 없음"]
    raw, body = m.group(1), text[m.end():]
    fields: dict = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not km:
            errors.append(f"해석할 수 없는 frontmatter 줄: {line!r}")
            i += 1
            continue
        key, val = km.group(1), km.group(2).strip()
        i += 1
        block: list[str] = []
        while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
            block.append(lines[i])
            i += 1
        if val in (">", ">-", "|", "|-"):
            parts = [b.strip() for b in block]
            fields[key] = (" " if val.startswith(">") else "\n").join(p for p in parts if p)
        elif val == "" and block:
            sub = {}
            for b in block:
                sm = re.match(r"^\s+([A-Za-z0-9_-]+):\s*(.*)$", b)
                if sm:
                    sub[sm.group(1)] = sm.group(2).strip().strip('"').strip("'")
            fields[key] = sub
        else:
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            fields[key] = val
    return fields, body, errors


def read_text(p: Path) -> str:
    return io.open(p, encoding="utf-8").read()


def load_json(p: Path):
    return json.loads(read_text(p))


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print("FAIL:", msg)
    sys.exit(1)


def force_utf8_stdout() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
