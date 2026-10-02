#!/usr/bin/env python3
"""스킬 description 트리거 평가 (Windows 호환).

공식 skill-creator의 scripts/run_eval.py와 같은 방법을 쓴다:
임시 프로젝트의 .claude/commands/<이름>.md에 description을 넣고 `claude -p "<질문>"`을 실행해,
Claude가 그 명령(Skill 도구 또는 파일 Read)을 호출하면 '트리거됨'으로 본다.
원본 스크립트는 파이프에 select.select를 써서 Windows에서 동작하지 않으므로 스레드로 읽는다.

eval set: [{"query": "...", "should_trigger": true|false}, ...]
결과: --out <폴더>/results.json  {"description", "runs_per_query", "results": [{query, should_trigger, triggers, runs, rate}],
                                   "summary": {recall, false_positive_rate, ...}}

사용법
  python tools/run_trigger_eval.py --eval-set <json> --skill-path <스킬 폴더> --out <폴더>
         [--runs 3] [--workers 6] [--timeout 90] [--model claude-opus-5-5]
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import parse_frontmatter, read_text  # noqa: E402


def claude_exe() -> str:
    for n in ("claude.exe", "claude.cmd", "claude"):
        p = shutil.which(n)
        if p:
            return p
    raise SystemExit("claude CLI를 찾을 수 없습니다")


def one_run(query: str, name: str, desc: str, timeout: int, model: str | None) -> bool:
    proj = Path(tempfile.mkdtemp(prefix="trig-"))
    clean = f"{name}-skill-{uuid.uuid4().hex[:8]}"
    cmd_dir = proj / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    body = "\n  ".join(desc.split("\n"))
    (cmd_dir / f"{clean}.md").write_text(f"---\ndescription: |\n  {body}\n---\n\n# {name}\n\nThis skill handles: {desc}\n",
                                         encoding="utf-8")
    args = [claude_exe(), "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    if model:
        args += ["--model", model]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    proc = subprocess.Popen(args, cwd=proj, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    lines: queue.Queue = queue.Queue()

    def reader():
        for raw in iter(proc.stdout.readline, b""):
            lines.put(raw.decode("utf-8", "replace"))
        lines.put(None)

    threading.Thread(target=reader, daemon=True).start()
    triggered = False
    pending, acc = None, ""
    start = time.time()
    try:
        while time.time() - start < timeout:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                continue
            if line is None:
                break
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "stream_event":
                se = ev.get("event", {})
                t = se.get("type", "")
                if t == "content_block_start":
                    cb = se.get("content_block", {})
                    pending = cb.get("name") if cb.get("type") == "tool_use" and cb.get("name") in ("Skill", "Read") else None
                    acc = ""
                    if cb.get("type") == "tool_use" and cb.get("name") not in ("Skill", "Read"):
                        break  # 다른 도구를 먼저 썼다 = 이 스킬을 고르지 않았다
                elif t == "content_block_delta" and pending:
                    acc += se.get("delta", {}).get("partial_json", "")
                    if clean in acc:
                        triggered = True
                        break
                elif t == "content_block_stop" and pending:
                    if clean in acc:
                        triggered = True
                    break
            elif ev.get("type") == "assistant":
                for c in ev.get("message", {}).get("content", []):
                    if c.get("type") == "tool_use" and clean in json.dumps(c.get("input", {})):
                        triggered = True
                break
            elif ev.get("type") == "result":
                break
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        shutil.rmtree(proj, ignore_errors=True)
    return triggered


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--skill-path", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--description")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--model")
    a = ap.parse_args(argv)
    fm, _, _ = parse_frontmatter(read_text(Path(a.skill_path) / "SKILL.md"))
    name, desc = fm["name"], a.description or fm["description"]
    items = json.loads(Path(a.eval_set).read_text(encoding="utf-8"))
    jobs = [(i, r) for i in range(len(items)) for r in range(a.runs)]
    hits: dict[int, list[bool]] = {i: [] for i in range(len(items))}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(one_run, items[i]["query"], name, desc, a.timeout, a.model): i for i, _ in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            i = futs[f]
            try:
                hits[i].append(f.result())
            except Exception as e:  # noqa: BLE001
                print(f"경고: 실행 실패 {e}", file=sys.stderr)
                hits[i].append(False)
            print(f"\r{n}/{len(jobs)}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    results = []
    for i, it in enumerate(items):
        rate = sum(hits[i]) / len(hits[i]) if hits[i] else 0
        results.append({"query": it["query"], "should_trigger": it["should_trigger"], "triggers": sum(hits[i]),
                        "runs": len(hits[i]), "rate": round(rate, 3)})
    pos = [r for r in results if r["should_trigger"]]
    neg = [r for r in results if not r["should_trigger"]]
    summary = {
        "recall": round(sum(r["rate"] >= 0.5 for r in pos) / len(pos), 3) if pos else None,
        "false_positive_rate": round(sum(r["rate"] >= 0.5 for r in neg) / len(neg), 3) if neg else None,
        "mean_trigger_rate_pos": round(sum(r["rate"] for r in pos) / len(pos), 3) if pos else None,
        "mean_trigger_rate_neg": round(sum(r["rate"] for r in neg) / len(neg), 3) if neg else None,
        "queries": len(results), "runs_per_query": a.runs, "model": a.model or "default",
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"skill": name, "description": desc, "results": results, "summary": summary},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
    for r in results:
        ok = (r["rate"] >= 0.5) == r["should_trigger"]
        print(f"{'OK  ' if ok else 'MISS'} rate={r['rate']:.2f} expect={'Y' if r['should_trigger'] else 'N'}  {r['query'][:70]}")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
