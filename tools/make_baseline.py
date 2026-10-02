#!/usr/bin/env python3
"""v1.6.1 스킬 스냅샷(baseline)을 만든다.

Phase 1에서 스킬을 고칠 때 skill-creator의 'old_skill' 비교 대상으로 쓴다.
스냅샷은 git 태그에서 매번 재현되므로 저장소에 커밋하지 않는다(.workspace/는 .gitignore).

  .workspace/baseline/v1.6.1/<스킬명>/...

사용법
  python tools/make_baseline.py            # 생성(있으면 다시 만든다)
  python tools/make_baseline.py --verify   # 생성 후 태그의 모든 파일과 내용이 같은지 검증
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import BASELINE_TAG, LEGACY_SKILLS, ROOT, force_utf8_stdout, git  # noqa: E402

OUT = ROOT / ".workspace" / "baseline" / BASELINE_TAG


def build() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    data = git("archive", "--format=tar", BASELINE_TAG, "skills", binary=True)
    n = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            rel = Path(*Path(m.name).parts[1:])  # skills/ 접두사 제거
            dst = OUT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(tf.extractfile(m).read())  # type: ignore[union-attr]
            n += 1
    return n


def verify() -> list[str]:
    problems: list[str] = []
    entries = {}
    for line in git("ls-tree", "-r", BASELINE_TAG, "skills").splitlines():
        meta, path = line.split("\t", 1)
        entries[path] = meta.split()[2]
    for path, blob in entries.items():
        f = OUT / Path(*Path(path).parts[1:])
        if not f.is_file():
            problems.append(f"없음: {f}")
            continue
        # git archive도 core.autocrlf 변환을 적용하므로 같은 변환을 거친 해시로 비교한다.
        h = subprocess.run(["git", "hash-object", str(f)], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
        if h != blob:
            problems.append(f"내용 다름: {f}")
    for s in sorted({Path(p).parts[1] for p in entries}):  # v1.6.1 태그에 있던 스킬만
        if not (OUT / s / "SKILL.md").is_file():
            problems.append(f"SKILL.md 없음: {s}")
    extra = {p for p in OUT.rglob("*") if p.is_file()} - {OUT / Path(*Path(p).parts[1:]) for p in entries}
    problems += [f"태그에 없는 파일: {p}" for p in sorted(extra)]
    return problems


def main(argv: list[str]) -> int:
    force_utf8_stdout()
    n = build()
    print(f"baseline {BASELINE_TAG}: {n} files -> {OUT.relative_to(ROOT)}")
    if "--verify" in argv:
        problems = verify()
        for p in problems:
            print("FAIL:", p)
        if problems:
            return 1
        print("BASELINE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
