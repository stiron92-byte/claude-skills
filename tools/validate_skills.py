#!/usr/bin/env python3
"""정적 스킬 검증기 (계획서 §3.4 '정적 검사').

공식 `claude plugin validate`가 보지 않는 이 저장소의 규약을 검사한다.

규칙 (severity)
  fm-parse        (error)  frontmatter 해석 실패
  name            (error)  name 누락·형식 위반·디렉터리명 불일치·예약어(anthropic, claude)
  description     (error)  누락, 1,024자 초과, when_to_use 합산 1,536자 초과
  body-length     (error)  본문 500줄 초과
  fm-unknown-key  (warn)   알려지지 않은 frontmatter 키
  env-path        (error)  특정 환경 전용 경로·도구 하드코딩(/mnt/user-data, present_files, ~/Desktop 등)
  personal-path   (error)  개인 PC 절대 경로(/Users/<이름>, C:\\Users\\<이름>)
  broken-link     (error)  마크다운 링크가 가리키는 스킬 내 파일이 없음
  backslash-path  (warn)   문서 안의 Windows 백슬래시 경로
  secret          (error)  비밀 정보로 보이는 값
  model-id        (warn)   날짜가 박힌 모델 ID 하드코딩(시간이 지나면 폐기됨)

baseline
  Phase 0 시점의 기존 위반은 tools/validate-baseline.json에 동결한다. 검증은 baseline에 없는
  '새' 위반만 실패로 본다. Phase 1에서 스킬을 고칠 때마다 --update-baseline으로 목록을 줄인다.
  키는 줄 번호가 아니라 (규칙, 파일, 줄 내용)이라 줄이 이동해도 유지된다.

사용법
  python tools/validate_skills.py                                   # 전체 결과(모든 위반) 출력, error 있으면 exit 1
  python tools/validate_skills.py --baseline tools/validate-baseline.json   # 새 위반만 실패
  python tools/validate_skills.py --baseline tools/validate-baseline.json --update-baseline
  python tools/validate_skills.py --root <plugins 폴더>              # 다른 트리 검사(테스트용)
  python tools/validate_skills.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import PLUGINS_DIR, ROOT, SHARED_DIR, force_utf8_stdout, parse_frontmatter, read_text  # noqa: E402

sys.path.insert(0, str(SHARED_DIR / "scripts"))
from validate_overrides import SECRET_PATTERNS  # noqa: E402

KNOWN_KEYS = {
    "name", "description", "when_to_use", "license", "compatibility", "metadata", "allowed-tools",
    "disallowed-tools", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "model", "effort", "context", "agent", "background", "paths", "shell", "hooks", "version",
}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENV_PATTERNS = [
    re.compile(r"/mnt/user-data"),
    re.compile(r"/mnt/skills"),
    re.compile(r"/home/claude\b"),
    re.compile(r"\bpresent_files\b"),
    re.compile(r"computer://"),
    re.compile(r"~/Desktop"),
]
PERSONAL_PATH = re.compile(r"(/Users/(?!Shared/)[A-Za-z0-9._-]+/|[A-Za-z]:\\\\?Users\\\\?[A-Za-z0-9._-]+\\\\)")
BACKSLASH_PATH = re.compile(r"(?<![\\`])\b[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+")
MODEL_ID = re.compile(r"\bclaude-[a-z0-9-]+-20\d{6}\b")
MD_LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
TEXT_EXT = {".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt", ".toml", ".example"}
SKIP_PARTS = {"_vendor", "_shared", "__pycache__", "samples"}  # vendoring 사본·실습 샘플은 검사 제외


def finding(rule, sev, skill, file, line_no, line, msg):
    return {"rule": rule, "severity": sev, "skill": skill, "file": file, "line": line_no,
            "text": line.strip()[:200], "message": msg}


def key_of(f: dict) -> str:
    h = hashlib.sha1(f["text"].encode("utf-8")).hexdigest()[:12]
    return f"{f['rule']}|{f['file']}|{h}"


def iter_text_files(skill_root: Path):
    for p in sorted(skill_root.rglob("*")):
        if not p.is_file() or SKIP_PARTS & set(p.relative_to(skill_root).parts):
            continue
        if p.suffix in TEXT_EXT or p.name.endswith(".env.example"):
            yield p


def check_skill(skill_root: Path, base: Path) -> list[dict]:
    out: list[dict] = []
    skill = skill_root.name
    rel = lambda p: p.relative_to(base).as_posix()  # noqa: E731
    md = skill_root / "SKILL.md"
    text = read_text(md)
    fm, body, errs = parse_frontmatter(text)
    for e in errs:
        out.append(finding("fm-parse", "error", skill, rel(md), 1, e, e))
    name = fm.get("name", "")
    if not name:
        out.append(finding("name", "error", skill, rel(md), 1, "name", "name 누락"))
    else:
        if not NAME_RE.match(name) or len(name) > 64:
            out.append(finding("name", "error", skill, rel(md), 1, f"name: {name}", "소문자·숫자·하이픈 64자 이하"))
        if name != skill:
            out.append(finding("name", "error", skill, rel(md), 1, f"name: {name}", f"디렉터리명({skill})과 다름"))
        if "anthropic" in name or "claude" in name:
            out.append(finding("name", "error", skill, rel(md), 1, f"name: {name}", "예약어 포함"))
    desc = fm.get("description", "")
    if not isinstance(desc, str) or not desc.strip():
        out.append(finding("description", "error", skill, rel(md), 1, "description", "description 누락"))
    else:
        if len(desc) > 1024:
            out.append(finding("description", "error", skill, rel(md), 1, "description",
                               f"{len(desc)}자 > 1024"))
        wtu = fm.get("when_to_use", "")
        if isinstance(wtu, str) and len(desc) + len(wtu) > 1536:
            out.append(finding("description", "error", skill, rel(md), 1, "description+when_to_use",
                               f"합산 {len(desc) + len(wtu)}자 > 1536"))
    for k in fm:
        if k not in KNOWN_KEYS:
            out.append(finding("fm-unknown-key", "warn", skill, rel(md), 1, k, f"알려지지 않은 키 {k}"))
    n_body = len(body.splitlines())
    if n_body > 500:
        out.append(finding("body-length", "error", skill, rel(md), 1, f"body {n_body} lines", f"본문 {n_body}줄 > 500"))

    for p in iter_text_files(skill_root):
        content = p.read_text(encoding="utf-8", errors="replace")
        is_md = p.suffix == ".md"
        for i, line in enumerate(content.splitlines(), 1):
            for pat in ENV_PATTERNS:
                if pat.search(line):
                    out.append(finding("env-path", "error", skill, rel(p), i, line, f"환경 전용 표기 '{pat.pattern}'"))
                    break
            if PERSONAL_PATH.search(line):
                out.append(finding("personal-path", "error", skill, rel(p), i, line, "개인 PC 절대 경로"))
            for name_, pat in SECRET_PATTERNS:
                if pat.search(line):
                    out.append(finding("secret", "error", skill, rel(p), i, line, f"비밀 정보 의심({name_})"))
                    break
            if MODEL_ID.search(line):
                out.append(finding("model-id", "warn", skill, rel(p), i, line, "날짜가 박힌 모델 ID"))
            if is_md:
                if BACKSLASH_PATH.search(line) and "\\n" not in line:
                    out.append(finding("backslash-path", "warn", skill, rel(p), i, line, "백슬래시 경로"))
                for target in MD_LINK.findall(line):
                    if re.match(r"^[a-z]+:", target) or target.startswith("/"):
                        continue
                    if not (p.parent / target).exists():
                        out.append(finding("broken-link", "error", skill, rel(p), i, line, f"링크 대상 없음: {target}"))
    return out


def discover(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/skills/*/SKILL.md"))


def main(argv: list[str]) -> int:
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(PLUGINS_DIR))
    ap.add_argument("--baseline")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    base = root.parent
    skills = discover(root)
    if not skills:
        print(f"FAIL: 스킬을 찾지 못함: {root}")
        return 1
    findings = [f for s in skills for f in check_skill(s, base)]
    allowed: set[str] = set()
    if a.baseline and Path(a.baseline).is_file() and not a.update_baseline:
        allowed = set(json.loads(Path(a.baseline).read_text(encoding="utf-8"))["allowed"])
    if a.update_baseline:
        if not a.baseline:
            print("--update-baseline에는 --baseline 경로가 필요합니다")
            return 2
        keys = sorted({key_of(f) for f in findings})
        Path(a.baseline).write_text(json.dumps({
            "note": "Phase 0 시점 기존 위반 동결 목록. Phase 1에서 고칠 때마다 줄인다. 새 위반은 여기에 추가하지 않는다.",
            "allowed": keys}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"baseline updated: {len(keys)} entries")
        return 0
    new = [f for f in findings if key_of(f) not in allowed]
    new_errors = [f for f in new if f["severity"] == "error"]
    stale = sorted(allowed - {key_of(f) for f in findings})
    summary = {
        "skills": len(skills),
        "findings_total": len(findings),
        "errors_total": sum(1 for f in findings if f["severity"] == "error"),
        "baselined": len(findings) - len(new),
        "new_errors": len(new_errors),
        "new_warnings": len(new) - len(new_errors),
        "stale_baseline_entries": len(stale),
    }
    if a.json:
        print(json.dumps({"summary": summary, "new": new, "stale": stale}, ensure_ascii=False, indent=2))
    else:
        for f in new:
            print(f"{f['severity'].upper():5} {f['rule']:<15} {f['file']}:{f['line']}  {f['message']}")
        if stale:
            print(f"INFO  baseline에서 해결된 항목 {len(stale)}개 — --update-baseline으로 목록을 줄이세요")
        print("summary:", json.dumps(summary, ensure_ascii=False))
    if new_errors:
        print("VALIDATE FAILED")
        return 1
    print("VALIDATE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
