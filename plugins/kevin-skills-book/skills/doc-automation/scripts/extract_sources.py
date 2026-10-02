#!/usr/bin/env python3
"""입력 자료를 '출처 ID가 붙은 텍스트 묶음'으로 추출한다.

보고서의 모든 숫자·주장은 출처로 거슬러 올라갈 수 있어야 한다. 그래서 첫 단계에서
파일마다 S01, S02 … ID를 붙이고, 페이지·슬라이드·표 위치 표시를 남긴 마크다운으로 저장한다.
이후 스토리라인(outline.json)은 이 ID로 출처를 적고, verify_deck.py는 이 텍스트로 숫자를 대조한다.

지원 형식
  문서: .pdf .docx .pptx .hwpx .html .htm .md .txt
  표:   .csv .tsv .xlsx .xls .json   (열 목록, 행 수, 수치 요약, 앞 30행 표)
  이미지: .png .jpg .jpeg .gif .svg   (텍스트 없음, 자산으로 목록만 — 로고 등)
  폴더를 주면 안의 지원 파일을 모두 처리한다.

출력
  <out>/sources.json       [{id, file, path, kind, chars, md, note}]
  <out>/S01.md, S02.md …   추출 텍스트(마크다운)

사용법
  python extract_sources.py <파일 또는 폴더> [...] --out <작업폴더>/sources
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "_vendor"))

DOC_EXT = {".pdf", ".docx", ".pptx", ".hwpx", ".html", ".htm", ".md", ".txt"}
TAB_EXT = {".csv", ".tsv", ".xlsx", ".xls", ".json"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
UNSUPPORTED_HINT = {
    ".hwp": "구버전 한글(.hwp)은 읽지 못합니다. 한컴오피스에서 HWPX로 다시 저장해 주세요.",
    ".doc": "구버전 Word(.doc)는 읽지 못합니다. .docx로 다시 저장해 주세요.",
    ".ppt": "구버전 PowerPoint(.ppt)는 읽지 못합니다. .pptx로 다시 저장해 주세요.",
}


class MissingDependency(RuntimeError):
    pass


def _need(module: str, pip_name: str):
    try:
        return __import__(module)
    except ImportError as e:
        raise MissingDependency(f"{pip_name} 패키지가 필요합니다: python -m pip install {pip_name} "
                                f"(doctor 스킬로 전체 점검 가능)") from e


def _md_table(rows: list[list], header: list | None = None) -> str:
    def cell(v) -> str:
        s = "" if v is None else str(v)
        return s.replace("|", "\\|").replace("\n", " ").strip()
    if not rows and not header:
        return ""
    header = header or rows[0]
    body = rows if header is not rows[0] else rows[1:]
    out = ["| " + " | ".join(cell(h) for h in header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in body]
    return "\n".join(out)


def read_pdf(p: Path) -> str:
    pdfplumber = _need("pdfplumber", "pdfplumber")
    parts = []
    with pdfplumber.open(p) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            parts.append(f"\n[p.{i}]\n" + (page.extract_text() or "").strip())
            for j, tb in enumerate(page.extract_tables() or [], 1):
                if tb and len(tb) > 1:
                    parts.append(f"\n[p.{i} 표{j}]\n" + _md_table(tb))
    return "\n".join(parts).strip()


def read_docx(p: Path) -> str:
    docx = _need("docx", "python-docx")
    d = docx.Document(str(p))
    parts = []
    for para in d.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        style = (para.style.name or "").lower() if para.style is not None else ""
        if style.startswith("heading") or style.startswith("제목"):
            level = "".join(ch for ch in style if ch.isdigit()) or "2"
            parts.append("#" * min(int(level) + 1, 6) + " " + t)
        else:
            parts.append(t)
    for j, tb in enumerate(d.tables, 1):
        rows = [[c.text for c in r.cells] for r in tb.rows]
        if rows:
            parts.append(f"\n[표{j}]\n" + _md_table(rows))
    return "\n\n".join(parts)


def read_pptx(p: Path) -> str:
    pptx = _need("pptx", "python-pptx")
    prs = pptx.Presentation(str(p))
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for sh in slide.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                texts.append(sh.text_frame.text.strip())
            if getattr(sh, "has_table", False) and sh.has_table:
                texts.append(_md_table([[c.text for c in r.cells] for r in sh.table.rows]))
            if getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                try:
                    cats = list(ch.plots[0].categories)
                    for s in ch.plots[0].series:
                        texts.append(f"[차트 {s.name}] " + ", ".join(f"{c}: {v}" for c, v in zip(cats, s.values)))
                except Exception:  # noqa: BLE001
                    pass
        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            notes = "\n(노트) " + slide.notes_slide.notes_text_frame.text.strip()
        parts.append(f"\n[slide {i}]\n" + "\n".join(texts) + notes)
    return "\n".join(parts).strip()


def read_hwpx(p: Path) -> str:
    from hwpx_parser import extract_text  # vendored
    return extract_text(str(p))


def read_html(p: Path) -> str:
    bs4 = _need("bs4", "beautifulsoup4")
    soup = bs4.BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        t.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = [l.strip() for l in main.get_text("\n").splitlines()]
    return "\n".join(l for l in lines if l)


def read_text(p: Path) -> str:
    for enc in ("utf-8", "cp949"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")


def read_table(p: Path) -> tuple[str, str]:
    pd = _need("pandas", "pandas")
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xls"):
        sheets = pd.read_excel(p, sheet_name=None)
    elif ext == ".json":
        sheets = {"json": pd.read_json(p)}
    else:
        sep = "\t" if ext == ".tsv" else ","
        try:
            sheets = {"data": pd.read_csv(p, sep=sep)}
        except UnicodeDecodeError:
            sheets = {"data": pd.read_csv(p, sep=sep, encoding="cp949")}
    parts, notes = [], []
    for name, df in sheets.items():
        parts.append(f"\n[시트 {name}] {len(df)}행 × {len(df.columns)}열")
        parts.append("열: " + ", ".join(map(str, df.columns)))
        num = df.select_dtypes("number")
        if not num.empty:
            desc = num.agg(["sum", "mean", "min", "max"]).T.round(2)
            parts.append("수치 요약(합계·평균·최소·최대):\n" + _md_table(
                [[c] + [v for v in desc.loc[c]] for c in desc.index], header=["열", "합계", "평균", "최소", "최대"]))
        head = df.head(30)
        parts.append("앞 30행:\n" + _md_table(head.astype(object).where(head.notna(), "").values.tolist(),
                                              header=list(map(str, df.columns))))
        if len(df) > 30:
            notes.append(f"{name}: 전체 {len(df)}행 중 30행만 표시 — 집계는 원본 파일로 계산할 것")
    return "\n".join(parts).strip(), "; ".join(notes)


def extract(paths: list[Path], out: Path) -> list[dict]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.is_file())
        elif p.is_file():
            files.append(p)
        else:
            raise SystemExit(f"입력을 찾을 수 없습니다: {p}")
    out.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    n = 0
    for f in files:
        ext = f.suffix.lower()
        if ext not in DOC_EXT | TAB_EXT | IMG_EXT:
            if ext in UNSUPPORTED_HINT:
                manifest.append({"id": None, "file": f.name, "path": str(f.resolve()), "kind": "unsupported",
                                 "chars": 0, "md": None, "note": UNSUPPORTED_HINT[ext]})
            continue
        n += 1
        sid = f"S{n:02d}"
        note = ""
        try:
            if ext in IMG_EXT:
                kind, text = "image", ""
                note = "이미지 자산(로고·사진). 슬라이드에 넣을 수 있음"
            elif ext in TAB_EXT:
                kind = "table"
                text, note = read_table(f)
            else:
                kind = "document"
                text = {".pdf": read_pdf, ".docx": read_docx, ".pptx": read_pptx, ".hwpx": read_hwpx,
                        ".html": read_html, ".htm": read_html}.get(ext, read_text)(f)
        except MissingDependency as e:
            kind, text, note = "error", "", str(e)
        except Exception as e:  # noqa: BLE001 — 한 파일 실패가 전체를 막지 않게
            kind, text, note = "error", "", f"추출 실패: {type(e).__name__}: {e}"
        md_path = None
        if kind in ("document", "table"):
            md_path = out / f"{sid}.md"
            md_path.write_text(f"# {sid} — {f.name}\n\n{text}\n", encoding="utf-8")
            if not text.strip():
                note = (note + "; " if note else "") + "추출된 텍스트가 없음(스캔 PDF일 수 있음 — 이미지로 읽어 확인)"
        manifest.append({"id": sid, "file": f.name, "path": str(f.resolve()), "kind": kind,
                         "chars": len(text), "md": md_path.name if md_path else None, "note": note})
    (out / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="입력 자료 → 출처 ID 텍스트 묶음")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    m = extract([Path(x) for x in a.inputs], Path(a.out))
    for e in m:
        print(f"{e['id'] or '--':4} {e['kind']:<11} {e['chars']:>7}자  {e['file']}  {e['note']}")
    bad = [e for e in m if e["kind"] in ("error", "unsupported")]
    print(f"\n{len(m) - len(bad)}개 추출, 문제 {len(bad)}개 → {Path(a.out) / 'sources.json'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
