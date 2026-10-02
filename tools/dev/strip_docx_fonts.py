#!/usr/bin/env python3
"""DOCX에 내장된 글꼴 파일(word/fonts/*)을 제거한다.

왜: 예제 docx 6개가 각각 Google Sans 글꼴 4종(약 2.9MB)을 내장하고 있어
플러그인 용량의 대부분을 차지하고, 글꼴 재배포 라이선스 문제도 생길 수 있다.
글꼴을 빼도 문서는 열리며 시스템 대체 글꼴로 표시된다.

처리 내용
- word/fonts/* 파트 삭제
- word/fontTable.xml 의 <w:embed*> 요소 삭제
- word/_rels/fontTable.xml.rels 에서 fonts/ 관계 삭제
- word/settings.xml 의 <w:embedTrueTypeFonts/>, <w:saveSubsetFonts/> 삭제
- [Content_Types].xml 에서 글꼴 Override 및 더 이상 쓰이지 않는 글꼴 확장자 Default 삭제

그 외 파트는 바이트 그대로 복사한다. 원본은 임시 파일로 쓴 뒤 교체한다.

사용법: python tools/dev/strip_docx_fonts.py <docx> [<docx> ...]
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import zipfile

FONT_EXTS = ("odttf", "ttf", "otf", "fntdata")


def strip(path: str) -> tuple[int, int]:
    before = os.path.getsize(path)
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        font_parts = [n for n in names if n.startswith("word/fonts/")]
        if not font_parts:
            return before, before
        fd, tmp = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(path) or ".")
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp, "w") as zout:
                for info in zin.infolist():
                    n = info.filename
                    if n in font_parts:
                        continue
                    data = zin.read(n)
                    if n == "word/fontTable.xml":
                        s = data.decode("utf-8")
                        s = re.sub(r"<w:embed(?:Regular|Bold|Italic|BoldItalic)\b[^>]*/>", "", s)
                        data = s.encode("utf-8")
                    elif n == "word/_rels/fontTable.xml.rels":
                        s = data.decode("utf-8")
                        s = re.sub(r'<Relationship\b[^>]*Target="fonts/[^"]*"[^>]*/>', "", s)
                        data = s.encode("utf-8")
                    elif n == "word/settings.xml":
                        s = data.decode("utf-8")
                        s = re.sub(r"<w:(?:embedTrueTypeFonts|saveSubsetFonts)\b[^>]*/>", "", s)
                        data = s.encode("utf-8")
                    elif n == "[Content_Types].xml":
                        s = data.decode("utf-8")
                        s = re.sub(r'<Override\b[^>]*PartName="/word/fonts/[^"]*"[^>]*/>', "", s)
                        remaining = [m for m in names if m not in font_parts]
                        for ext in FONT_EXTS:
                            if not any(m.lower().endswith("." + ext) for m in remaining):
                                s = re.sub(rf'<Default\b[^>]*Extension="{ext}"[^>]*/>', "", s, flags=re.I)
                        data = s.encode("utf-8")
                    zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
    # 원본 zip 핸들을 닫은 뒤 교체한다(Windows는 열린 파일을 교체할 수 없다).
    os.replace(tmp, path)
    return before, os.path.getsize(path)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    total_before = total_after = 0
    for p in argv:
        b, a = strip(p)
        total_before += b
        total_after += a
        print(f"{p}: {b // 1024}KB -> {a // 1024}KB")
    print(f"TOTAL {total_before // 1024}KB -> {total_after // 1024}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
