#!/usr/bin/env python3
"""오버라이드 폴더 검사 — 사용자 맞춤 파일을 팀에 공유하기 전에 실행한다.

검사 항목
- error: 허용되지 않은 파일 형식(실행 파일·스크립트)
- error: settings 파일 해석 실패
- error: 비밀 정보로 보이는 값(API 키, 토큰, Slack Webhook 등)
- warning: 보호 규칙을 무력화하려는 것으로 보이는 문장(예: "원본을 덮어써도 된다")

오버라이드는 '데이터와 지식'만 바꾼다. 실행 코드(.py, .sh 등)는 오버라이드로 넣지 않는다.
실행 코드를 바꿔야 하면 계획서 §8.2의 L3(스킬 복제) 단계로 간다.

CLI: python validate_overrides.py <오버라이드 폴더> [--json]
종료 코드: 오류 0건이면 0, 아니면 1
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from overrides import SETTINGS_NAMES, load_settings_file  # noqa: E402

ALLOWED_EXT = {
    ".md", ".txt", ".yaml", ".yml", ".json", ".csv",
    ".pptx", ".potx", ".docx", ".dotx", ".xlsx", ".hwpx",
    ".png", ".jpg", ".jpeg", ".svg", ".ttf", ".otf", ".ttc",
}

SECRET_PATTERNS = [
    ("anthropic-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("slack-token", re.compile(r"xox[abposr]-[A-Za-z0-9-]{10,}")),
    ("slack-webhook", re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]+")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    # key = "리터럴" 형태만 잡는다. os.environ.get(...) 같은 코드, ${ENV}·<자리표시자>는 제외한다.
    ("generic-quoted", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd|webhook[_-]?url)\b[\"']?\s*[:=]\s*[\"'](?![$<{])[^\s\"']{8,}[\"']")),
    # YAML·.env 의 따옴표 없는 값: 숫자를 포함한 16자 이상 토큰(변수 이름과 구분하기 위해)
    ("generic-unquoted", re.compile(
        r"(?i)^\s*(api[_-]?key|secret|token|password|passwd|webhook[_-]?url)\s*[:=]\s*(?![$<{\"'])(?=[^\s#]*\d)[^\s#(]{16,}\s*(#.*)?$")),
]

# 보호 규칙 무력화 의심 문장(한국어·영어). 경고만 낸다 — 사람이 판단한다.
WEAKENING_PATTERNS = [
    ("no-overwrite-original", re.compile(r"원본[을를]?\s*(그대로\s*)?덮어[써쓰].{0,10}(된다|됩니다|허용|해도)|overwrite (the )?original", re.I)),
    ("no-secrets-in-files", re.compile(r"(api\s*키|토큰|webhook).{0,20}(파일|config|설정)에\s*(저장|기록|적어)", re.I)),
    ("no-investment-advice", re.compile(r"(매수|매도)\s*(추천|권유|의견).{0,10}(포함|작성|제시)하", re.I)),
    ("confirm-before-external-send", re.compile(r"(확인\s*없이|묻지\s*말고).{0,20}(전송|업로드|보내)", re.I)),
    ("no-silent-data-fix", re.compile(r"(이상값|오타).{0,20}(자동으로\s*수정|바로\s*고쳐)", re.I)),
]


def scan(folder: str | Path) -> dict:
    folder = Path(folder)
    errors: list[dict] = []
    warnings: list[dict] = []
    files = [f for f in sorted(folder.rglob("*")) if f.is_file()] if folder.is_dir() else []
    if not folder.is_dir():
        errors.append({"file": str(folder), "issue": "폴더가 없습니다"})
    for f in files:
        rel = f.relative_to(folder).as_posix()
        if f.suffix.lower() not in ALLOWED_EXT:
            errors.append({"file": rel, "issue": f"허용되지 않은 형식 {f.suffix or '(확장자 없음)'} — 실행 코드는 오버라이드로 넣지 않습니다"})
            continue
        if f.name in SETTINGS_NAMES:
            try:
                load_settings_file(f)
            except Exception as e:  # noqa: BLE001
                errors.append({"file": rel, "issue": f"설정 해석 실패: {e}"})
        if f.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".svg"}:
            text = f.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                for name, pat in SECRET_PATTERNS:
                    if pat.search(line):
                        errors.append({"file": rel, "line": n, "issue": f"비밀 정보로 보이는 값({name}) — 환경 변수나 플러그인 설정으로 옮기세요"})
                        break
                for rule, pat in WEAKENING_PATTERNS:
                    if pat.search(line):
                        warnings.append({"file": rel, "line": n, "issue": f"보호 규칙 '{rule}'과 충돌할 수 있는 문장 — 이 규칙은 오버라이드로 바뀌지 않습니다"})
    return {"folder": str(folder), "files": len(files), "errors": errors, "warnings": warnings}


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    res = scan(argv[0])
    if "--json" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for e in res["errors"]:
            print(f"ERROR {e['file']}{':' + str(e['line']) if 'line' in e else ''}  {e['issue']}")
        for w in res["warnings"]:
            print(f"WARN  {w['file']}:{w['line']}  {w['issue']}")
        status = "OVERRIDES OK" if not res["errors"] else "OVERRIDES INVALID"
        print(f"{status} ({res['files']} files, {len(res['errors'])} errors, {len(res['warnings'])} warnings)")
    return 0 if not res["errors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
