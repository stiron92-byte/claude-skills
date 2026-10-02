#!/usr/bin/env python3
"""사전 점검(doctor) — 스킬을 쓰기 전에 이 PC의 준비 상태를 확인한다.

강의 전날 수강생이, 또는 사내 사용자가 처음 설치한 뒤 실행한다.
각 항목을 ok / warn / fail 로 판정하고, 실패하면 이 OS에서 실행할 해결 명령을 함께 보여 준다.

판정 기준
- fail: 해당 스킬의 핵심 기능이 동작하지 않는다
- warn: 일부 선택 기능만 영향을 받는다
- ok:   준비됨

CLI
  python doctor.py                      # 전체 점검(표)
  python doctor.py --skills doc-automation meeting-minutes
  python doctor.py --json               # 기계 판독용
  python doctor.py --network            # 네트워크 도달성도 확인(외부 접속 발생)
  python doctor.py --strict             # fail이 하나라도 있으면 exit 1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fonts  # noqa: E402
from env import detect  # noqa: E402

SYSTEM = platform.system()


def _pip(pkg: str) -> str:
    return f"python -m pip install {pkg}"


# 스킬별 요구사항: (종류, 이름, 필수 여부, 해결 명령 또는 OS별 dict)
REQUIREMENTS: dict[str, list[tuple]] = {
    "doc-automation": [
        ("py", "pptx", True, _pip("python-pptx")),
        ("py", "pandas", True, _pip("pandas")),
        ("py", "matplotlib", True, _pip("matplotlib")),
        ("py", "openpyxl", True, _pip("openpyxl")),
        ("py", "docx", True, _pip("python-docx")),
        ("py", "pdfplumber", True, _pip("pdfplumber")),
        ("py", "bs4", False, _pip("beautifulsoup4")),
        ("font", "korean", True, None),
    ],
    "hwpx-editor": [],
    "excel-automation": [
        ("py", "pandas", True, _pip("pandas")),
        ("py", "openpyxl", True, _pip("openpyxl")),
        ("exe", "soffice", False, {"Windows": "winget install TheDocumentFoundation.LibreOffice",
                                   "Darwin": "brew install --cask libreoffice",
                                   "Linux": "sudo apt-get install -y libreoffice-calc"}),
    ],
    "meeting-minutes": [  # 음성 디코딩은 faster-whisper에 포함된 PyAV가 하므로 ffmpeg는 필요 없다
        ("py", "faster_whisper", False, _pip("faster-whisper")),
        ("py", "docx", False, _pip("python-docx")),
    ],
    "data-collector": [
        ("py", "yaml", True, _pip("pyyaml")),
    ],
    "content-research": [
        ("py", "feedparser", False, _pip("feedparser")),
        ("py", "yaml", True, _pip("pyyaml")),
    ],
    "content-repurpose": [],
    "generate-shorts": [
        ("exe", "ffmpeg", True, {"Windows": "winget install Gyan.FFmpeg",
                                 "Darwin": "brew install ffmpeg",
                                 "Linux": "sudo apt-get install -y ffmpeg"}),
        ("exe", "yt-dlp", True, {"Windows": _pip("yt-dlp"), "Darwin": _pip("yt-dlp"), "Linux": _pip("yt-dlp")}),
        ("py", "PIL", True, _pip("Pillow")),
        ("py", "edge_tts", False, _pip("edge-tts")),
        ("font", "korean", True, None),
    ],
    "narration-video": [
        ("exe", "uv", True, {"Windows": "winget install astral-sh.uv",
                             "Darwin": "brew install uv",
                             "Linux": "python -m pip install uv"}),
        ("exe", "ffmpeg", True, {"Windows": "winget install Gyan.FFmpeg",
                                 "Darwin": "brew install ffmpeg",
                                 "Linux": "sudo apt-get install -y ffmpeg"}),
        ("font", "korean", True, None),
    ],
}

NETWORK_TARGETS = [
    ("pypi", "https://pypi.org/simple/pip/", "패키지 설치"),
    ("youtube", "https://www.youtube.com/", "generate-shorts"),
    ("gemini", "https://generativelanguage.googleapis.com/", "narration-video"),
]


def _fix(fix) -> str | None:
    if isinstance(fix, dict):
        return fix.get(SYSTEM) or next(iter(fix.values()))
    return fix


def check_python() -> dict:
    ok = sys.version_info >= (3, 10)
    return {"id": "python", "status": "ok" if ok else "fail",
            "detail": f"Python {platform.python_version()} ({sys.executable})",
            "fix": None if ok else "Python 3.10 이상을 설치하세요: https://www.python.org/downloads/"}


def check_output_writable() -> dict:
    try:
        with tempfile.NamedTemporaryFile(dir=os.getcwd(), prefix=".doctor-", delete=True):
            pass
        return {"id": "output-writable", "status": "ok", "detail": f"작업 폴더 쓰기 가능: {os.getcwd()}", "fix": None}
    except OSError as e:
        return {"id": "output-writable", "status": "fail", "detail": f"작업 폴더에 쓸 수 없음: {e}",
                "fix": "쓰기 권한이 있는 폴더(예: 문서 폴더 아래 새 폴더)에서 다시 실행하세요."}


def check_disk(min_gb: float = 2.0) -> dict:
    free = shutil.disk_usage(os.getcwd()).free / 1024**3
    status = "ok" if free >= min_gb else "warn"
    return {"id": "disk-free", "status": status, "detail": f"남은 공간 {free:.1f}GB",
            "fix": None if status == "ok" else f"영상·STT 모델용으로 {min_gb}GB 이상 확보를 권장합니다."}


def check_item(kind: str, name: str, required: bool, fix) -> dict:
    bad = "fail" if required else "warn"
    if kind == "py":
        found = importlib.util.find_spec(name) is not None
        return {"id": f"py:{name}", "status": "ok" if found else bad,
                "detail": f"Python 패키지 {name} {'있음' if found else '없음'}", "fix": None if found else _fix(fix)}
    if kind == "exe":
        path = shutil.which(name)
        return {"id": f"exe:{name}", "status": "ok" if path else bad,
                "detail": f"{name}: {path or '찾을 수 없음'}", "fix": None if path else _fix(fix)}
    if kind == "font":
        info = fonts.describe()
        return {"id": "font:korean", "status": "ok" if info["regular"] else bad,
                "detail": f"한글 폰트: {info['regular'] or '없음'}", "fix": info["hint"]}
    raise ValueError(kind)


def check_network(timeout: float = 5.0) -> list[dict]:
    out = []
    for name, url, purpose in NETWORK_TARGETS:
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "claude-skills-doctor"})
            urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 — 고정된 https URL만 사용
            out.append({"id": f"net:{name}", "status": "ok", "detail": f"{url} 접속 가능", "fix": None})
        except urllib.error.HTTPError as e:  # 응답이 왔으면 도달은 가능
            out.append({"id": f"net:{name}", "status": "ok", "detail": f"{url} 응답 {e.code}", "fix": None})
        except Exception as e:  # noqa: BLE001
            out.append({"id": f"net:{name}", "status": "warn", "detail": f"{url} 접속 실패({purpose}): {e}",
                        "fix": "사내망이면 프록시 설정(HTTPS_PROXY)을 확인하거나 오프라인 실습 모드를 사용하세요."})
    return out


def run(skills: list[str] | None = None, network: bool = False) -> dict:
    skills = skills or list(REQUIREMENTS)
    unknown = [s for s in skills if s not in REQUIREMENTS]
    if unknown:
        raise SystemExit(f"알 수 없는 스킬: {', '.join(unknown)} (가능: {', '.join(REQUIREMENTS)})")
    results = [check_python(), check_output_writable(), check_disk()]
    base_status = [r["status"] for r in results if r["id"] in ("python", "output-writable")]
    skill_status: dict[str, str] = {}
    seen: dict[str, dict] = {}
    for s in skills:
        sts = list(base_status)
        for kind, name, required, fix in REQUIREMENTS[s]:
            r = check_item(kind, name, required, fix)
            sts.append(r["status"])  # 스킬 판정은 그 스킬의 필수/선택 기준으로만 한다
            prev = seen.get(r["id"])
            # 표에 한 번만 보이는 항목은 가장 엄격한 판정을 남긴다
            if prev is None or (prev["status"] != "fail" and r["status"] == "fail"):
                seen[r["id"]] = r
        skill_status[s] = "fail" if "fail" in sts else ("warn" if "warn" in sts else "ok")
    results.extend(seen.values())
    if network:
        results.extend(check_network())
    counts = {k: sum(1 for r in results if r["status"] == k) for k in ("ok", "warn", "fail")}
    return {"environment": detect(), "checks": results, "skills": skill_status, "counts": counts}


def render(report: dict) -> str:
    mark = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}
    lines = [f"환경: {report['environment']['surface']} / {report['environment']['os']} / Python {report['environment']['python']}", ""]
    for r in report["checks"]:
        lines.append(f"[{mark[r['status']]}] {r['id']:<22} {r['detail']}")
        if r["fix"]:
            lines.append(f"        해결: {r['fix']}")
    lines.append("")
    lines.append("스킬별 준비 상태:")
    for s, st in report["skills"].items():
        lines.append(f"  {mark[st]} {s}")
    c = report["counts"]
    lines.append(f"\n요약: ok {c['ok']} · warn {c['warn']} · fail {c['fail']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="claude-skills 사전 점검")
    ap.add_argument("--skills", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--network", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    report = run(a.skills, a.network)
    print(json.dumps(report, ensure_ascii=False, indent=2) if a.json else render(report))
    return 1 if (a.strict and report["counts"]["fail"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
