#!/usr/bin/env python3
"""pptx 슬라이드를 PNG 이미지로 렌더링한다 — 눈으로 하는 최종 검수용.

verify_deck.py는 구조와 숫자를 검사하지만 '보기에 이상한지'(겹침, 잘림, 빈 공간)는 이미지로 봐야 안다.
렌더링한 PNG를 열어 슬라이드마다 확인한다.

백엔드(있는 것을 순서대로 시도)
1. Windows PowerPoint (COM 자동화, PowerShell)
2. LibreOffice(soffice) → PDF → PNG (pdftoppm 또는 PyMuPDF가 있으면)
둘 다 없으면 종료 코드 2와 함께 안내한다. 그때는 verify_deck 결과만으로 판단하고 사용자에게 직접 확인을 요청한다.

사용법
  python render_slides.py report.pptx --out <폴더> [--width 1280]
출력: <폴더>/slide-01.png …, 마지막 줄 RENDER OK <장수>
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def via_powerpoint(pptx: Path, out: Path, width: int) -> list[Path]:
    if platform.system() != "Windows" or not shutil.which("powershell"):
        return []
    height = int(width * 9 / 16)
    tmp = Path(tempfile.mkdtemp(prefix="render-"))
    ps = f"""
$ErrorActionPreference = 'Stop'
$pp = New-Object -ComObject PowerPoint.Application
try {{
  $pres = $pp.Presentations.Open('{pptx.resolve()}', $true, $false, $false)
  $w = {width}; $h = [int]($w * $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth)
  $pres.Export('{tmp}', 'PNG', $w, $h)
  $pres.Close()
}} finally {{ $pp.Quit() }}
"""
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return []
    files = sorted(tmp.glob("*.PNG"), key=lambda p: int("".join(ch for ch in p.stem if ch.isdigit()) or 0))
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for i, f in enumerate(files, 1):
        dst = out / f"slide-{i:02d}.png"
        shutil.move(str(f), dst)
        result.append(dst)
    shutil.rmtree(tmp, ignore_errors=True)
    return result


def via_soffice(pptx: Path, out: Path, width: int) -> list[Path]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return []
    tmp = Path(tempfile.mkdtemp(prefix="render-"))
    r = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(pptx)],
                       capture_output=True, text=True, timeout=300)
    pdf = tmp / (pptx.stem + ".pdf")
    if r.returncode != 0 or not pdf.is_file():
        return []
    out.mkdir(parents=True, exist_ok=True)
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-scale-to", str(width), str(pdf), str(out / "slide")], check=True)
        files = sorted(out.glob("slide-*.png"))
        return [f.rename(out / f"slide-{i:02d}.png") for i, f in enumerate(files, 1)]
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return []
    doc = fitz.open(str(pdf))
    result = []
    for i, page in enumerate(doc, 1):
        zoom = width / page.rect.width
        dst = out / f"slide-{i:02d}.png"
        page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(str(dst))
        result.append(dst)
    return result


def main(argv: list[str]) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="pptx → 슬라이드 PNG")
    ap.add_argument("pptx")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1280)
    a = ap.parse_args(argv)
    pptx, out = Path(a.pptx), Path(a.out)
    if not pptx.is_file():
        print(f"오류: 파일이 없습니다: {pptx}")
        return 1
    for name, fn in (("PowerPoint", via_powerpoint), ("LibreOffice", via_soffice)):
        try:
            files = fn(pptx, out, a.width)
        except (subprocess.SubprocessError, OSError):
            files = []
        if files:
            for f in files:
                print(f)
            print(f"RENDER OK {len(files)} ({name})")
            return 0
    print("RENDER UNAVAILABLE: PowerPoint(Windows)도 LibreOffice도 없어 이미지를 만들 수 없습니다. "
          "verify_deck 결과로 판단하고, 사용자에게 파일을 열어 확인해 달라고 요청하세요.")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
