#!/usr/bin/env python3
"""P8 오라클: skill-creator benchmark.json에서 새 스킬이 기존(old_skill)보다 나은지 판정한다.

조건
- with_skill과 비교 구성(old_skill 또는 without_skill)이 둘 다 있다
- 두 구성 모두 측정된 eval이 --min-evals 개 이상
- with_skill 평균 통과율 >= --min-pass, 그리고 비교 구성보다 높다
- 판단 대기(passed=None) 항목이 남아 있지 않다 → 각 run의 grading.json을 직접 확인
통과율은 benchmark.json의 runs[].result.pass_rate로 다시 계산한다(요약값을 그대로 믿지 않는다).

사용법: python tools/check_benchmark.py <benchmark.json> [--min-evals 3] [--min-pass 0.8]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("benchmark")
    ap.add_argument("--min-evals", type=int, default=3)
    ap.add_argument("--min-pass", type=float, default=0.8)
    a = ap.parse_args(argv)
    p = Path(a.benchmark)
    if not p.is_file():
        print(f"FAIL: benchmark 없음 {p}")
        return 1
    b = json.loads(p.read_text(encoding="utf-8"))
    by = defaultdict(dict)
    for r in b.get("runs", []):
        by[r["configuration"]].setdefault(r["eval_id"], []).append(r["result"]["pass_rate"])
    problems = []
    base_cfg = "old_skill" if "old_skill" in by else ("without_skill" if "without_skill" in by else None)
    if "with_skill" not in by or not base_cfg:
        print(f"FAIL: 구성 부족 {sorted(by)}")
        return 1
    common = sorted(set(by["with_skill"]) & set(by[base_cfg]))
    if len(common) < a.min_evals:
        problems.append(f"공통 eval {len(common)}개 < {a.min_evals}")
    mean = lambda cfg: sum(sum(v) / len(v) for k, v in by[cfg].items() if k in common) / max(1, len(common))  # noqa: E731
    w, o = mean("with_skill"), mean(base_cfg)
    if w < a.min_pass:
        problems.append(f"with_skill 평균 {w:.3f} < {a.min_pass}")
    if not w > o:
        problems.append(f"with_skill {w:.3f} 가 {base_cfg} {o:.3f} 보다 높지 않음")
    pending = 0
    for g in p.parent.glob("eval-*/*/run-*/grading.json"):
        pending += sum(1 for x in json.loads(g.read_text(encoding="utf-8"))["expectations"] if x["passed"] is None)
    if pending:
        problems.append(f"판단 대기 항목 {pending}개")
    for e in common:
        print(f"eval {e}: with_skill {sum(by['with_skill'][e]) / len(by['with_skill'][e]):.2f}  "
              f"{base_cfg} {sum(by[base_cfg][e]) / len(by[base_cfg][e]):.2f}")
    print(f"mean pass rate: with_skill {w:.3f} vs {base_cfg} {o:.3f} (delta {w - o:+.3f}) over {len(common)} evals")
    for x in problems:
        print("FAIL:", x)
    if problems:
        return 1
    print("BENCHMARK OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
