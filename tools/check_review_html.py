#!/usr/bin/env python3
"""P9 오라클: skill-creator 정적 eval 뷰어 HTML이 모든 실행을 담고 있는지 확인한다.

- HTML 파일이 있고 크기가 0이 아니다
- iteration 폴더의 모든 eval 이름과 구성 이름(with_skill, old_skill 등)이 HTML에 나온다
- 벤치마크 탭 데이터(pass_rate)가 들어 있다
사용법: python tools/check_review_html.py <review.html> <iteration 폴더>
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    if len(argv) != 2:
        print(__doc__)
        return 2
    html, it = Path(argv[0]), Path(argv[1])
    if not html.is_file() or html.stat().st_size == 0:
        print(f"FAIL: HTML 없음 {html}")
        return 1
    text = html.read_text(encoding="utf-8", errors="replace")
    problems = []
    runs = [r for r in it.glob("eval-*/*/run-*") if (r / "outputs").is_dir()]
    if not runs:
        problems.append("실행 폴더가 없음")
    for r in runs:
        eval_name = r.parent.parent.name.removeprefix("eval-")
        if eval_name not in text:
            problems.append(f"eval 이름 없음: {eval_name}")
        if r.parent.name not in text:
            problems.append(f"구성 이름 없음: {r.parent.name}")
    if "pass_rate" not in text:
        problems.append("벤치마크 데이터(pass_rate) 없음")
    for x in sorted(set(problems)):
        print("FAIL:", x)
    if problems:
        return 1
    print(f"runs covered: {len(runs)}, size {html.stat().st_size // 1024}KB")
    print("REVIEW HTML OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
