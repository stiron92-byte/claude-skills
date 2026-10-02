"""excel-automation 테스트 공통 경로·실행 도우미."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/kevin-skills-book/skills/excel-automation"
SCRIPTS = SKILL / "scripts"
INPUTS = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/excel-automation/inputs"
P1 = INPUTS / "실습1_고객관리_원본.xlsx"
P2 = INPUTS / "실습2_쇼핑몰매출_원본.xlsx"
P3 = INPUTS / "실습3_멀티채널판매_원본.xlsx"
KEY = json.loads((INPUTS / "answer_key.json").read_text(encoding="utf-8"))

CONSOLIDATE_SPEC = {
    "key": "상품코드",
    "sheets": [
        {"sheet": "상품마스터", "columns": {"상품명": "상품명", "카테고리": "카테고리"}},
        {"sheet": "재고현황", "columns": {"총재고": "총재고"}},
        {"sheet": "스마트스토어", "columns": {"3월판매량": "스마트스토어_판매량", "3월매출": "스마트스토어_매출"}},
        {"sheet": "쿠팡", "columns": {"3월판매량": "쿠팡_판매량", "3월매출": "쿠팡_매출"}},
        {"sheet": "카카오선물하기", "columns": {"3월판매량": "카카오선물하기_판매량", "3월매출": "카카오선물하기_매출"}},
        {"sheet": "자사몰", "columns": {"3월판매량": "자사몰_판매량", "3월매출": "자사몰_매출"}},
    ],
    "sums": {"전체_판매량": ["스마트스토어_판매량", "쿠팡_판매량", "카카오선물하기_판매량", "자사몰_판매량"]},
    "count_nonblank": {"등록채널수": ["스마트스토어_판매량", "쿠팡_판매량", "카카오선물하기_판매량", "자사몰_판매량"]},
}


def run_script(name: str, *args) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=600)


def engine_available() -> bool:
    import platform
    import shutil
    if os.environ.get("CLAUDE_SKILLS_NO_RECALC"):
        return False  # CI·테스트에서 엔진 없는 경로를 강제
    if shutil.which("soffice") or shutil.which("libreoffice"):
        return True
    if platform.system() == "Windows":
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "try { $x = New-Object -ComObject Excel.Application; $x.Quit(); 'YES' } catch { 'NO' }"],
                           capture_output=True, text=True, timeout=120)
        return "YES" in r.stdout
    return False
