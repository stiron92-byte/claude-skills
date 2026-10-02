#!/usr/bin/env python3
"""HWPX 결과 검증 — 원본 양식이 보존되었고 요청한 글자만 바뀌었는지 확인한다.

검사 항목(오류)
- 결과가 ZIP으로 열리고, 첫 엔트리가 무압축 mimetype이며 내용이 원본과 같다
- 엔트리 목록이 원본과 같다(추가·삭제 없음)
- 바뀐 엔트리는 XML로 해석되며, 선언된 네임스페이스 접두사(xmlns:*)가 원본과 같다
- 바뀌지 않아야 할 엔트리(이미지, 설정, 바꾸지 않은 XML)는 내용이 바이트 단위로 같다
- --map을 주면: 각 새 텍스트가 결과에 있고, 원본 텍스트는 (새 텍스트의 일부가 아닌 한) 결과에 남아 있지 않다
- 결과에 {{자리표시자}}가 남아 있지 않다(--allow-placeholders로 끌 수 있음)

CLI: python verify_hwpx.py 원본.hwpx 결과.hwpx [--map map.json] [--json]
종료 코드: 통과 0, 실패 1
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwpx_template import TEXT_NODE, _content_xml_names, _load_map, _visible  # noqa: E402

XMLNS = re.compile(r'xmlns:(\w+)="([^"]+)"')


def texts(zf: zipfile.ZipFile) -> str:
    out = []
    for n in _content_xml_names(zf):
        xml = zf.read(n).decode("utf-8", errors="replace")
        out += [_visible(m.group("body")) for m in TEXT_NODE.finditer(xml)]
    return "\n".join(out)


def verify(src: str, dst: str, mapping: list[tuple[str, str]] | None = None,
           allow_placeholders: bool = False) -> dict:
    errors: list[str] = []
    info: dict = {}
    try:
        zo, zn = zipfile.ZipFile(src), zipfile.ZipFile(dst)
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        return {"ok": False, "errors": [f"열 수 없음: {e}"], "info": {}}
    with zo, zn:
        first = zn.infolist()[0] if zn.infolist() else None
        if not first or first.filename != "mimetype":
            errors.append("첫 엔트리가 mimetype이 아님(한컴오피스가 형식을 인식하지 못할 수 있음)")
        elif first.compress_type != zipfile.ZIP_STORED:
            errors.append("mimetype이 압축되어 있음(무압축이어야 함)")
        elif "mimetype" in zo.namelist() and zn.read("mimetype") != zo.read("mimetype"):
            errors.append("mimetype 내용이 원본과 다름")
        on, nn = set(zo.namelist()), set(zn.namelist())
        if on != nn:
            errors.append(f"엔트리 목록이 다름: 추가 {sorted(nn - on)[:5]}, 삭제 {sorted(on - nn)[:5]}")
        changed = []
        for name in sorted(on & nn):
            a, b = zo.read(name), zn.read(name)
            if a == b:
                continue
            changed.append(name)
            if name == "Preview/PrvText.txt":
                # 탐색기 미리보기 평문 — 본문과 같은 치환이 적용되는 것이 정상. UTF-8로 읽히는지만 본다
                try:
                    b.decode("utf-8")
                except UnicodeDecodeError:
                    errors.append("미리보기 텍스트가 UTF-8이 아님")
                continue
            if not name.lower().endswith(".xml"):
                errors.append(f"XML이 아닌 엔트리가 바뀜: {name}")
                continue
            try:
                ET.fromstring(b)
            except ET.ParseError as e:
                errors.append(f"{name}: XML 오류 {e}")
            if set(XMLNS.findall(a.decode("utf-8", "replace"))) != set(XMLNS.findall(b.decode("utf-8", "replace"))):
                errors.append(f"{name}: 네임스페이스 선언이 바뀜(한컴오피스에서 열리지 않을 수 있음)")
            # 태그 구조 보존: 텍스트 노드 본문과 linesegarray를 뺀 나머지 골격이 같아야 한다
            def skeleton(x: bytes) -> str:
                s = x.decode("utf-8", "replace")
                s = re.sub(r"<(\w+:)?linesegarray\b.*?</(\w+:)?linesegarray>|<(\w+:)?linesegarray\b[^>]*/>", "", s, flags=re.S)
                return TEXT_NODE.sub(lambda m: m.group(1) + m.group(4), s)
            if skeleton(a) != skeleton(b):
                errors.append(f"{name}: 텍스트 외 XML 구조(태그·속성)가 바뀜")
        info["changed_entries"] = changed
        new_text = texts(zn)
        if mapping:
            for old, new in mapping:
                if new and new not in new_text:
                    errors.append(f"새 텍스트가 결과에 없음: {new!r}")
                if old and old in new_text and not any(old in n for _, n in mapping):
                    errors.append(f"원본 텍스트가 남아 있음: {old!r}")
        if not allow_placeholders:
            left = sorted(set(re.findall(r"\{\{(\w+)\}\}", new_text)))
            if left:
                errors.append(f"채우지 않은 자리표시자: {left}")
        info["changed_count"] = len(changed)
    return {"ok": not errors, "errors": errors, "info": info}


def main(argv: list[str]) -> int:
    import argparse
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("output")
    ap.add_argument("--map")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-placeholders", action="store_true")
    a = ap.parse_args(argv)
    res = verify(a.original, a.output, _load_map(a.map) if a.map else None, a.allow_placeholders)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for e in res["errors"]:
            print("ERROR", e)
        print(f"바뀐 엔트리: {res['info'].get('changed_entries')}")
        print("HWPX VERIFY OK" if res["ok"] else "HWPX VERIFY FAILED")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
