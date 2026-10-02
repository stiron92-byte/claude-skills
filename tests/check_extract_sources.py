#!/usr/bin/env python3
"""P1 오라클: extract_sources.py가 실습 입력 형식을 모두 출처 ID 텍스트로 추출하는지 확인한다."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/kevin-skills-book/skills/doc-automation/scripts/extract_sources.py"
S = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/doc-automation"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inp = td / "in"
        inp.mkdir()
        for f in (S / "example/example_3_comany-to-ppt").iterdir():
            shutil.copy2(f, inp / f.name)
        shutil.copy2(S / "example/example_1_pdf-to-ppt/260316_FX_weekly(KOR).pdf", inp)
        shutil.copy2(S / "example/example_2_url-to-ppt/삼성전자_투자분석_보고.pptx", inp)
        shutil.copy2(S / "samples/weekly_sales.csv", inp)
        shutil.copy2(S / "example/example_4_hwpx-template/원본_결재문서본문.hwpx", inp)
        (inp / "page.html").write_text("<html><head><script>var secret=1;</script></head><body><nav>메뉴</nav>"
                                       "<main><h1>환율 동향</h1><p>달러/원 1,452.3원</p></main></body></html>", encoding="utf-8")
        (inp / "memo.md").write_text("# 메모\n매출 4,520만 원", encoding="utf-8")
        (inp / "old.hwp").write_bytes(b"\xd0\xcf\x11\xe0")
        out = td / "sources"
        r = subprocess.run([sys.executable, str(SCRIPT), str(inp), "--out", str(out)], capture_output=True,
                           text=True, encoding="utf-8")
        man = json.loads((out / "sources.json").read_text(encoding="utf-8"))
        by = {e["file"]: e for e in man}
        ids = [e["id"] for e in man if e["id"]]
        if ids != [f"S{i:02d}" for i in range(1, len(ids) + 1)]:
            problems.append(f"ID가 연속이 아님: {ids}")

        def text(fname: str) -> str:
            e = by.get(fname)
            return (out / e["md"]).read_text(encoding="utf-8") if e and e.get("md") else ""

        docx = [f for f in by if f.endswith(".docx")]
        if len(docx) != 6 or any(by[f]["kind"] != "document" or by[f]["chars"] < 100 for f in docx):
            problems.append("docx 6개 추출 실패")
        pdf = text("260316_FX_weekly(KOR).pdf")
        if "[p.1]" not in pdf or len(pdf) < 1000:
            problems.append("PDF 페이지 표시·본문 부족")
        if "[slide 1]" not in text("삼성전자_투자분석_보고.pptx"):
            problems.append("PPTX 슬라이드 표시 없음")
        csv = text("weekly_sales.csv")
        if "열:" not in csv or "수치 요약" not in csv:
            problems.append("CSV 요약 누락")
        if "서울대공원" not in text("원본_결재문서본문.hwpx"):
            problems.append("HWPX 본문 추출 실패")
        h = text("page.html")
        if "1,452.3" not in h or "secret" in h or "메뉴" in h:
            problems.append("HTML 본문 추출·잡음 제거 실패")
        if "4,520" not in text("memo.md"):
            problems.append("MD 추출 실패")
        enc = by.get("2026년+팁스+창업기업+지원계획+공고.hwpx", {})
        if enc.get("kind") != "error" or "배포용" not in enc.get("note", ""):
            problems.append(f"암호화 HWPX 안내 실패: {enc}")
        if by.get("7. 로고.png", {}).get("kind") != "image":
            problems.append("이미지 자산 인식 실패")
        if by.get("old.hwp", {}).get("kind") != "unsupported" or "HWPX" not in by["old.hwp"]["note"]:
            problems.append(".hwp 안내 실패")
        if r.returncode != 1:
            problems.append(f"문제 파일이 있는데 종료 코드 {r.returncode}")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    print(f"sources={len(man)} ids={len(ids)} kinds={sorted({e['kind'] for e in man})}")
    print("EXTRACT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
