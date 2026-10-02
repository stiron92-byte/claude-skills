#!/usr/bin/env python3
"""P10 오라클: run_trigger_eval.py 결과(results.json)에서 적중률·오발동률을 판정한다.

- recall: should_trigger=true 질의 중 발동률 0.5 이상인 비율 >= --min-recall
- false positive rate: should_trigger=false 질의 중 발동률 0.5 이상인 비율 <= --max-fpr
- 질의마다 실제로 1회 이상 실행되었다(runs > 0)
summary 값을 믿지 않고 results에서 다시 계산한다.
사용법: python tools/check_trigger_results.py <results.json> [--min-recall 0.8] [--max-fpr 0.2]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--min-recall", type=float, default=0.8)
    ap.add_argument("--max-fpr", type=float, default=0.2)
    a = ap.parse_args(argv)
    p = Path(a.results)
    if not p.is_file():
        print(f"FAIL: 결과 없음 {p}")
        return 1
    rs = json.loads(p.read_text(encoding="utf-8"))["results"]
    if any(r["runs"] == 0 for r in rs):
        print("FAIL: 실행되지 않은 질의가 있음")
        return 1
    pos = [r for r in rs if r["should_trigger"]]
    neg = [r for r in rs if not r["should_trigger"]]
    recall = sum(r["rate"] >= 0.5 for r in pos) / len(pos) if pos else 0
    fpr = sum(r["rate"] >= 0.5 for r in neg) / len(neg) if neg else 1
    print(f"recall {recall:.2f} ({len(pos)}), false positive rate {fpr:.2f} ({len(neg)})")
    ok = recall >= a.min_recall and fpr <= a.max_fpr and pos and neg
    if not ok:
        print("FAIL: 기준 미달")
        return 1
    print("TRIGGER OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
