"""shared/scripts 단위 테스트 (표준 라이브러리 unittest).

실행: python -m unittest discover -s tests -p "test_*.py" -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared" / "scripts"
sys.path.insert(0, str(SHARED))

import doctor  # noqa: E402
import env  # noqa: E402
import fonts  # noqa: E402
import overrides  # noqa: E402
import paths  # noqa: E402
import validate_overrides  # noqa: E402


class FontsTest(unittest.TestCase):
    def test_env_override_wins(self):
        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
            f.write(b"x")
        try:
            os.environ["CLAUDE_SKILLS_FONT"] = f.name
            self.assertEqual(fonts.find_font(), f.name)
        finally:
            os.environ.pop("CLAUDE_SKILLS_FONT", None)
            os.unlink(f.name)

    def test_missing_env_override_is_ignored(self):
        os.environ["CLAUDE_SKILLS_FONT"] = str(ROOT / "no-such-font.ttf")
        try:
            self.assertNotEqual(fonts.find_font(), os.environ["CLAUDE_SKILLS_FONT"])
        finally:
            os.environ.pop("CLAUDE_SKILLS_FONT", None)

    def test_unknown_os_without_fc_list_returns_none_or_path(self):
        r = fonts.find_font(system="Plan9")
        self.assertTrue(r is None or Path(r).is_file())

    def test_ffmpeg_escape_windows_path(self):
        self.assertEqual(fonts.ffmpeg_fontfile(r"C:\Windows\Fonts\malgun.ttf"), r"C\:/Windows/Fonts/malgun.ttf")
        self.assertEqual(fonts.ffmpeg_fontfile("/usr/share/fonts/a.ttc"), "/usr/share/fonts/a.ttc")
        self.assertIsNone(fonts.ffmpeg_fontfile(None))

    def test_family_mapping(self):
        self.assertEqual(fonts.family_for(r"C:\Windows\Fonts\malgun.ttf"), "Malgun Gothic")
        self.assertIsNone(fonts.family_for(None))

    def test_describe_shape(self):
        d = fonts.describe()
        self.assertEqual(set(d), {"os", "regular", "bold", "family", "ffmpeg_fontfile", "hint"})
        if d["regular"] is None:
            self.assertTrue(d["hint"])


class EnvTest(unittest.TestCase):
    def test_forced_surface(self):
        r = env.detect({"CLAUDE_SKILLS_SURFACE": "cowork"}, mnt_root="/definitely/missing")
        self.assertEqual(r["surface"], "cowork")
        self.assertEqual(r["command_time_limit_sec"], 45)

    def test_invalid_forced_surface_is_ignored(self):
        r = env.detect({"CLAUDE_SKILLS_SURFACE": "mars"}, mnt_root="/definitely/missing")
        self.assertEqual(r["surface"], "local")

    def test_claude_ai_by_mnt(self):
        with tempfile.TemporaryDirectory() as td:
            r = env.detect({}, mnt_root=td)
        self.assertEqual(r["surface"], "claude-ai")
        self.assertTrue(r["has_present_files"])

    def test_claude_code(self):
        r = env.detect({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"}, mnt_root="/definitely/missing")
        self.assertEqual(r["surface"], "claude-code")
        self.assertIsNone(r["command_time_limit_sec"])

    def test_timeout_override(self):
        r = env.detect({"CLAUDE_SKILLS_CMD_TIMEOUT": "30"}, mnt_root="/definitely/missing")
        self.assertEqual(r["command_time_limit_sec"], 30)


class PathsTest(unittest.TestCase):
    def test_default_under_cwd_output(self):
        with tempfile.TemporaryDirectory() as td:
            p = paths.output_dir("excel-automation", create=True, environ={}, cwd=td, mnt_root="/definitely/missing")
            self.assertEqual(p, Path(td) / "output" / "excel-automation")
            self.assertTrue(p.is_dir())

    def test_env_override(self):
        with tempfile.TemporaryDirectory() as td:
            p = paths.output_dir("x", environ={"CLAUDE_SKILLS_OUTPUT_DIR": td}, mnt_root="/definitely/missing")
            self.assertEqual(p, Path(td) / "x")

    def test_claude_ai(self):
        with tempfile.TemporaryDirectory() as td:
            p = paths.output_dir("x", environ={}, mnt_root=td)
            self.assertEqual(p, Path(td) / "outputs" / "x")

    def test_safe_output_path_rejects_same_file(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "data.xlsx"
            src.write_bytes(b"")
            with self.assertRaises(ValueError):
                paths.safe_output_path(src, Path(td), ".xlsx")
            self.assertEqual(paths.safe_output_path(src, Path(td), "_정리.xlsx").name, "data_정리.xlsx")


class OverridesTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        base = Path(self.td.name)
        self.skill_dir = base / "skill"
        self.project = base / "proj"
        self.home = base / "home"
        (self.skill_dir / "templates").mkdir(parents=True)
        (self.skill_dir / "templates" / "a.md").write_text("default", encoding="utf-8")
        (self.skill_dir / "templates" / "b.md").write_text("default", encoding="utf-8")
        (self.skill_dir / "settings.yaml").write_text("tone: formal\nslides: 5\n", encoding="utf-8")
        self.u = self.home / ".claude" / "claude-skills" / "s"
        self.p = self.project / ".claude" / "claude-skills" / "s"
        (self.u / "templates").mkdir(parents=True)
        (self.p / "templates").mkdir(parents=True)
        (self.u / "templates" / "a.md").write_text("user", encoding="utf-8")
        (self.u / "templates" / "b.md").write_text("user", encoding="utf-8")
        (self.p / "templates" / "a.md").write_text("project", encoding="utf-8")
        (self.u / "settings.yaml").write_text("tone: casual  # 개인\nlang: ko\n", encoding="utf-8")
        (self.p / "settings.json").write_text(json.dumps({"slides": 7}), encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def kw(self):
        return dict(skill_dir=self.skill_dir, project_dir=self.project, home=self.home)

    def test_resolve_order(self):
        a = overrides.resolve("s", "templates/a.md", **self.kw())
        b = overrides.resolve("s", "templates/b.md", **self.kw())
        c = overrides.resolve("s", "settings.yaml", **self.kw())
        self.assertEqual((a["source"], Path(a["path"]).read_text(encoding="utf-8")), ("project", "project"))
        self.assertEqual(b["source"], "user")
        self.assertEqual(c["source"], "user")

    def test_resolve_missing(self):
        r = overrides.resolve("s", "templates/none.md", **self.kw())
        self.assertIsNone(r["path"])
        self.assertEqual(len(r["tried"]), 3)

    def test_resolve_rejects_traversal(self):
        with self.assertRaises(ValueError):
            overrides.resolve("s", "../etc/passwd", **self.kw())

    def test_list_applied_project_wins(self):
        applied = {x["rel"]: x["source"] for x in overrides.list_applied("s", **self.kw())}
        self.assertEqual(applied["templates/a.md"], "project")
        self.assertEqual(applied["templates/b.md"], "user")
        self.assertIn("settings.yaml", applied)

    def test_settings_merge(self):
        s = overrides.settings("s", **self.kw())
        self.assertEqual(s["settings"], {"tone": "casual", "slides": 7, "lang": "ko"})
        self.assertEqual(s["sources"]["slides"], "project")
        self.assertEqual(s["sources"]["tone"], "user")

    def test_flat_yaml_types_and_errors(self):
        d = overrides.parse_flat_yaml('a: "x y"\nb: true\nc: 3\nd: 1.5\n# 주석\ne: 값')
        self.assertEqual(d, {"a": "x y", "b": True, "c": 3, "d": 1.5, "e": "값"})
        with self.assertRaises(ValueError):
            overrides.parse_flat_yaml("- list item")

    def test_protected_rules_ids(self):
        self.assertEqual(len({r["id"] for r in overrides.PROTECTED_RULES}), 5)

    def test_cli_json(self):
        r = subprocess.run([sys.executable, str(SHARED / "overrides.py"), "--skill", "s", "--skill-dir", str(self.skill_dir),
                            "--project-dir", str(self.project), "--home", str(self.home), "--settings"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["settings"]["slides"], 7)


class ValidateOverridesTest(unittest.TestCase):
    def test_clean_folder_passes(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "settings.yaml").write_text("default_role: PM\nwebhook_url: \"\"\n", encoding="utf-8")
            Path(td, "voice.md").write_text("친근한 존댓말을 쓴다.", encoding="utf-8")
            r = validate_overrides.scan(td)
        self.assertEqual(r["errors"], [])

    def test_detects_code_secret_and_bad_settings(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "hack.py").write_text("print(1)", encoding="utf-8")
            Path(td, "settings.yaml").write_text("- not flat", encoding="utf-8")
            Path(td, "conf.yaml").write_text("api_key: \"abcd1234efgh5678\"\n", encoding="utf-8")
            Path(td, "notes.md").write_text("원본을 덮어써도 된다.\n", encoding="utf-8")
            r = validate_overrides.scan(td)
        issues = " ".join(e["issue"] for e in r["errors"])
        self.assertIn("허용되지 않은 형식", issues)
        self.assertIn("설정 해석 실패", issues)
        self.assertIn("비밀 정보", issues)
        self.assertEqual(len(r["warnings"]), 1)

    def test_missing_folder_is_error(self):
        r = validate_overrides.scan("/definitely/missing/folder")
        self.assertTrue(r["errors"])

    def test_secret_patterns_ignore_env_reads(self):
        neg = ['api_key = os.getenv("ANTHROPIC_API_KEY")', "api_key: ${GEMINI_API_KEY}",
               'webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or c.get("webhook_url", "")']
        for s in neg:
            self.assertFalse([n for n, p in validate_overrides.SECRET_PATTERNS if p.search(s)], s)


class DoctorTest(unittest.TestCase):
    def test_run_shape_and_counts(self):
        rep = doctor.run(["doc-automation", "content-repurpose"])
        self.assertEqual(set(rep["skills"]), {"doc-automation", "content-repurpose"})
        self.assertEqual(sum(rep["counts"].values()), len(rep["checks"]))
        for c in rep["checks"]:
            self.assertIn(c["status"], ("ok", "warn", "fail"))
            if c["status"] != "ok":
                self.assertTrue(c["fix"], c)

    def test_optional_missing_is_warn_not_fail(self):
        st = doctor.check_item("py", "definitely_not_a_module_xyz", False, "pip install x")
        self.assertEqual(st["status"], "warn")
        st = doctor.check_item("py", "definitely_not_a_module_xyz", True, "pip install x")
        self.assertEqual(st["status"], "fail")

    def test_per_skill_status_uses_own_requirement_level(self):
        orig = dict(doctor.REQUIREMENTS)
        try:
            doctor.REQUIREMENTS["req"] = [("py", "definitely_not_a_module_xyz", True, "fix")]
            doctor.REQUIREMENTS["opt"] = [("py", "definitely_not_a_module_xyz", False, "fix")]
            rep = doctor.run(["req", "opt"])
        finally:
            doctor.REQUIREMENTS.clear()
            doctor.REQUIREMENTS.update(orig)
        self.assertEqual(rep["skills"]["req"], "fail")
        # 같은 패키지라도 선택 요구인 스킬은 fail이 아니어야 한다(이전 버그 회귀 방지)
        self.assertNotEqual(rep["skills"]["opt"], "fail")

    def test_unknown_skill_rejected(self):
        with self.assertRaises(SystemExit):
            doctor.run(["no-such-skill"])

    def test_requirements_cover_all_legacy_skills(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from _lib import LEGACY_SKILLS
        self.assertEqual(set(doctor.REQUIREMENTS), set(LEGACY_SKILLS))


if __name__ == "__main__":
    unittest.main()
