#!/usr/bin/env python3
"""실행 환경 감지.

스킬 지시가 claude.ai 컨테이너 경로(/mnt/user-data)나 특정 OS를 가정하면 다른 곳에서 틀린다.
이 모듈은 "지금 어디서 실행 중인가"를 근거와 함께 돌려준다. 확실하지 않으면 'unknown'이라고 말한다.

판정 근거
- claude.ai 컨테이너: /mnt/user-data 디렉터리 존재
- Claude Code(CLI·데스크톱): 환경 변수 CLAUDECODE=1, CLAUDE_CODE_ENTRYPOINT
- Cowork: 공식 식별 변수가 확인되지 않아 자동 판정하지 않는다. CLAUDE_SKILLS_SURFACE=cowork 로 지정한다.
- 수동 지정: CLAUDE_SKILLS_SURFACE (claude-ai | claude-code | cowork | local)

명령 시간 제한
- Cowork는 명령 하나당 약 45초 제한이 관찰되었다. CLAUDE_SKILLS_CMD_TIMEOUT(초)로 덮어쓸 수 있다.

CLI: python env.py  → JSON
"""
from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

SURFACES = ("claude-ai", "claude-code", "cowork", "local")
DEFAULT_TIMEOUTS = {"cowork": 45}


def detect(environ: dict | None = None, mnt_root: str = "/mnt/user-data") -> dict:
    env = os.environ if environ is None else environ
    evidence: list[str] = []
    surface = "unknown"
    forced = env.get("CLAUDE_SKILLS_SURFACE", "").strip().lower()
    if forced in SURFACES:
        surface = forced
        evidence.append(f"CLAUDE_SKILLS_SURFACE={forced}")
    elif Path(mnt_root).is_dir():
        surface = "claude-ai"
        evidence.append(f"{mnt_root} 존재")
    elif env.get("CLAUDECODE") == "1" or env.get("CLAUDE_CODE_ENTRYPOINT"):
        surface = "claude-code"
        evidence.append(f"CLAUDECODE={env.get('CLAUDECODE')}, CLAUDE_CODE_ENTRYPOINT={env.get('CLAUDE_CODE_ENTRYPOINT')}")
    else:
        surface = "local"
        evidence.append("Claude 관련 표식 없음(터미널 직접 실행으로 간주)")

    timeout = None
    raw = env.get("CLAUDE_SKILLS_CMD_TIMEOUT", "").strip()
    if raw.isdigit():
        timeout = int(raw)
        evidence.append(f"CLAUDE_SKILLS_CMD_TIMEOUT={raw}")
    else:
        timeout = DEFAULT_TIMEOUTS.get(surface)

    return {
        "surface": surface,
        "os": platform.system(),
        "python": platform.python_version(),
        "entrypoint": env.get("CLAUDE_CODE_ENTRYPOINT"),
        "command_time_limit_sec": timeout,
        "has_present_files": surface == "claude-ai",
        "evidence": evidence,
    }


def main() -> int:
    print(json.dumps(detect(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
