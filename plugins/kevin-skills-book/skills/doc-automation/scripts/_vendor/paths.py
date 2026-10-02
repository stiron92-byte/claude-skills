#!/usr/bin/env python3
"""스킬 출력 폴더 결정.

우선순위
1. CLAUDE_SKILLS_OUTPUT_DIR 환경 변수 (아래에 <스킬명>/ 하위 폴더를 만든다)
2. claude.ai 컨테이너: /mnt/user-data/outputs/<스킬명>/
3. 그 외: <현재 작업 폴더>/output/<스킬명>/

원본 파일과 같은 폴더에 결과를 쓰지 않는다. 원본을 덮어쓰는 사고를 막기 위해서다.

CLI: python paths.py <스킬명> [--create]   → 폴더 경로 출력
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import detect  # noqa: E402


def output_dir(skill: str, create: bool = False, environ: dict | None = None,
               cwd: str | None = None, mnt_root: str = "/mnt/user-data") -> Path:
    env = os.environ if environ is None else environ
    base_override = env.get("CLAUDE_SKILLS_OUTPUT_DIR")
    if base_override:
        base = Path(base_override)
    elif detect(env, mnt_root=mnt_root)["surface"] == "claude-ai":
        base = Path(mnt_root) / "outputs"
    else:
        base = Path(cwd or os.getcwd()) / "output"
    out = base / skill
    if create:
        out.mkdir(parents=True, exist_ok=True)
    return out


def safe_output_path(src: str | Path, out_dir: Path, suffix: str) -> Path:
    """원본 이름을 바탕으로 결과 파일 경로를 만든다. 원본과 같은 경로면 오류를 낸다."""
    src = Path(src)
    dst = out_dir / f"{src.stem}{suffix}"
    if dst.resolve() == src.resolve():
        raise ValueError(f"결과 경로가 원본과 같습니다: {dst}")
    return dst


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    print(output_dir(argv[0], create="--create" in argv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
