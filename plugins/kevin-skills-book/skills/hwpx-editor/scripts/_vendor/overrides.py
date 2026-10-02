#!/usr/bin/env python3
"""사용자 맞춤(오버라이드) 파일 탐색 — 계획서 §8.2 규약의 구현.

사용자가 플러그인 설치 폴더를 직접 고치면 업데이트 때 사라진다. 대신 아래 폴더에
같은 상대 경로로 파일을 두면 스킬이 그 파일을 우선 사용한다.

탐색 순서 (먼저 발견된 것 사용)
  1. 프로젝트:  <작업폴더>/.claude/claude-skills/<스킬명>/<상대경로>   ← 팀이 Git으로 공유
  2. 사용자:    ~/.claude/claude-skills/<스킬명>/<상대경로>             ← 개인 기본값
  3. 기본값:    <스킬 폴더>/<상대경로>

설정 값(settings.yaml 또는 settings.json)은 기본값 < 사용자 < 프로젝트 순으로 병합한다.

보호 규칙(PROTECTED_RULES)은 어떤 오버라이드로도 바꿀 수 없다.

CLI
  python overrides.py --skill doc-automation --skill-dir <스킬폴더> --list
  python overrides.py --skill doc-automation --skill-dir <스킬폴더> --resolve templates/email/team.md
  python overrides.py --skill doc-automation --skill-dir <스킬폴더> --settings
모든 출력은 JSON이다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

OVERRIDE_DIRNAME = Path(".claude") / "claude-skills"
SETTINGS_NAMES = ("settings.yaml", "settings.yml", "settings.json")

PROTECTED_RULES = [
    {"id": "no-overwrite-original", "rule": "원본 파일을 덮어쓰지 않는다. 결과는 항상 새 파일로 저장한다."},
    {"id": "no-secrets-in-files", "rule": "API 키·토큰·Webhook URL을 설정 파일이나 결과물에 기록하지 않는다."},
    {"id": "no-investment-advice", "rule": "특정 자산의 매수·매도를 권유하지 않는다."},
    {"id": "confirm-before-external-send", "rule": "개인정보·내부 문서를 외부 서비스로 보내기 전에 사용자에게 확인한다."},
    {"id": "no-silent-data-fix", "rule": "이상값·오타 후보를 사람 확인 없이 자동 수정하지 않는다."},
]


def roots(skill: str, skill_dir: str | Path, project_dir: str | Path | None = None,
          home: str | Path | None = None) -> list[tuple[str, Path]]:
    project = Path(project_dir or os.getcwd())
    home_p = Path(home or Path.home())
    return [
        ("project", project / OVERRIDE_DIRNAME / skill),
        ("user", home_p / OVERRIDE_DIRNAME / skill),
        ("default", Path(skill_dir)),
    ]


def _safe_rel(rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"상대 경로만 허용됩니다: {rel}")
    return p


def resolve(skill: str, rel: str, skill_dir: str | Path, project_dir=None, home=None) -> dict:
    relp = _safe_rel(rel)
    tried = []
    for source, base in roots(skill, skill_dir, project_dir, home):
        cand = base / relp
        tried.append(str(cand))
        if cand.is_file():
            return {"rel": rel, "source": source, "path": str(cand), "tried": tried}
    return {"rel": rel, "source": None, "path": None, "tried": tried}


def list_applied(skill: str, skill_dir: str | Path, project_dir=None, home=None) -> list[dict]:
    """프로젝트·사용자 폴더에 있는 오버라이드 파일 목록. 같은 상대 경로는 프로젝트가 이긴다."""
    seen: dict[str, dict] = {}
    for source, base in roots(skill, skill_dir, project_dir, home)[:2]:
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file():
                rel = f.relative_to(base).as_posix()
                if rel not in seen:
                    seen[rel] = {"rel": rel, "source": source, "path": str(f)}
    return list(seen.values())


def parse_flat_yaml(text: str) -> dict:
    """settings.yaml 용 단순 파서: 'key: value' 한 줄씩, # 주석, 따옴표, true/false/숫자 지원.

    중첩 구조가 필요하면 settings.json을 쓴다. 해석할 수 없는 줄은 ValueError.
    """
    out: dict = {}
    for n, line in enumerate(text.splitlines(), 1):
        s = line.split(" #", 1)[0].rstrip() if not line.lstrip().startswith("#") else ""
        if not s.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", s.strip())
        if not m:
            raise ValueError(f"{n}행: 'key: value' 형식이 아닙니다 → {line!r}")
        key, val = m.group(1), m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            v: object = val[1:-1]
        elif val.lower() in ("true", "false"):
            v = val.lower() == "true"
        elif re.fullmatch(r"-?\d+", val):
            v = int(val)
        elif re.fullmatch(r"-?\d+\.\d+", val):
            v = float(val)
        else:
            v = val
        out[key] = v
    return out


def load_settings_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"{path}: 최상위가 객체가 아닙니다")
        return data
    return parse_flat_yaml(text)


def settings(skill: str, skill_dir: str | Path, project_dir=None, home=None) -> dict:
    merged: dict = {}
    sources: dict = {}
    for source, base in reversed(roots(skill, skill_dir, project_dir, home)):  # default → user → project
        for name in SETTINGS_NAMES:
            p = base / name
            if p.is_file():
                data = load_settings_file(p)
                for k, v in data.items():
                    merged[k] = v
                    sources[k] = source
                break
    return {"settings": merged, "sources": sources}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="오버라이드 파일 탐색")
    ap.add_argument("--skill", required=True)
    ap.add_argument("--skill-dir", required=True)
    ap.add_argument("--project-dir")
    ap.add_argument("--home")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--resolve", metavar="REL")
    g.add_argument("--settings", action="store_true")
    g.add_argument("--protected", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        res: object = {"skill": a.skill, "applied": list_applied(a.skill, a.skill_dir, a.project_dir, a.home)}
    elif a.resolve:
        res = resolve(a.skill, a.resolve, a.skill_dir, a.project_dir, a.home)
    elif a.settings:
        res = settings(a.skill, a.skill_dir, a.project_dir, a.home)
    else:
        res = PROTECTED_RULES
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
