"""실습 샘플 복사와 vendoring 동기화 테스트."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/scripts/copy_samples.py"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class CopySamplesTest(unittest.TestCase):
    def test_catalog_complete(self):
        r = run(COPY, "--verify")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("CATALOG OK", r.stdout)

    def test_every_sample_file_is_in_catalog(self):
        """카탈로그에 없는 샘플 파일은 사용자가 찾을 방법이 없다."""
        samples = COPY.parents[1] / "samples"
        sys.path.insert(0, str(COPY.parent))
        import copy_samples  # noqa: E402
        covered = {p.resolve() for s in copy_samples.load() for pat in s["files"] for p in copy_samples.expand(pat)}
        all_files = {p.resolve() for p in samples.rglob("*") if p.is_file() and p.name != "catalog.json"}
        # 같은 파일의 중복본(example/서울불꽃축제_결과보고.hwpx)은 example_4 세트에 같은 이름으로 포함됨
        uncovered = sorted(p.relative_to(samples.resolve()).as_posix() for p in all_files - covered)
        self.assertEqual(uncovered, ["doc-automation/example/서울불꽃축제_결과보고.hwpx"])

    def test_copy_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            r1 = run(COPY, "--set", "doc-weekly-sales", "--dest", td)
            self.assertEqual(r1.returncode, 0, r1.stdout)
            res1 = json.loads(r1.stdout)[0]
            self.assertEqual(len(res1["copied"]), 3)
            target = Path(res1["copied"][0])
            target.write_text("사용자가 고친 내용", encoding="utf-8")
            r2 = run(COPY, "--set", "doc-weekly-sales", "--dest", td)
            res2 = json.loads(r2.stdout)[0]
            self.assertEqual(len(res2["skipped_existing"]), 3)
            self.assertEqual(target.read_text(encoding="utf-8"), "사용자가 고친 내용")

    def test_unknown_set(self):
        r = run(COPY, "--set", "nope")
        self.assertEqual(r.returncode, 2)


class BuildTest(unittest.TestCase):
    def test_vendor_in_sync(self):
        r = run(ROOT / "tools" / "build.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("VENDOR IN SYNC", r.stdout)


if __name__ == "__main__":
    unittest.main()
