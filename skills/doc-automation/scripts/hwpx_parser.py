#!/usr/bin/env python3
"""HWPX 파일 파서 — 텍스트, 표, 이미지 추출.

HWPX는 한컴 오피스의 XML 기반 문서 형식으로, ZIP 아카이브 내에
OWPML(Open Word-Processor Markup Language) XML 파일을 담고 있다.

외부 의존성 없이 stdlib(zipfile + xml.etree)만 사용한다.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# OWPML 네임스페이스 (한컴 오피스 버전에 따라 다를 수 있음)
# 실제 파일에서 동적으로 감지하되, 기본값을 정의한다.
DEFAULT_NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
}


def parse_hwpx(file_path: str) -> dict:
    """HWPX 파일을 파싱하여 구조화된 콘텐츠를 반환.

    Args:
        file_path: HWPX 파일 경로

    Returns:
        {
            "text": str,           # 전체 본문 텍스트
            "paragraphs": list,    # [{"text": str}, ...]
            "tables": list,        # [{"rows": [[cell, ...], ...]}, ...]
            "images": list,        # [{"path": str, "data": bytes}, ...]
            "metadata": dict,      # {"title": str, "author": str, ...}
        }

    Raises:
        ValueError: 유효한 HWPX 파일이 아닌 경우
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    if not zipfile.is_zipfile(file_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다 (ZIP 형식이 아님): {file_path}")

    with zipfile.ZipFile(file_path, "r") as zf:
        # 암호화 여부 확인
        if _is_encrypted(zf):
            raise ValueError("암호화된 HWPX 파일은 지원하지 않습니다.")

        ns = _detect_namespaces(zf)
        content_xmls = _find_content_xmls(zf)

        if not content_xmls:
            raise ValueError("HWPX 구조가 올바르지 않습니다 (content/section XML 없음)")

        paragraphs = []
        tables = []
        for xml_name in content_xmls:
            xml_bytes = zf.read(xml_name)
            root = ET.fromstring(xml_bytes)
            paragraphs.extend(_parse_paragraphs(root, ns))
            tables.extend(_parse_tables(root, ns))

        images = _extract_images(zf)
        metadata = _parse_metadata(zf)

    text = "\n".join(p["text"] for p in paragraphs if p["text"])

    return {
        "text": text,
        "paragraphs": paragraphs,
        "tables": tables,
        "images": images,
        "metadata": metadata,
    }


def extract_text(file_path: str) -> str:
    """HWPX에서 텍스트만 추출. analyze_data.py 연동용.

    표 데이터도 텍스트에 포함시킨다.
    """
    result = parse_hwpx(file_path)

    parts = []

    # 본문 텍스트
    if result["text"]:
        parts.append(result["text"])

    # 표 데이터를 텍스트로 변환
    for i, table in enumerate(result["tables"], 1):
        parts.append(f"\n[표 {i}]")
        for row in table["rows"]:
            parts.append(" | ".join(str(cell) for cell in row))

    return "\n\n".join(parts)


# ──────────────────────────────────────────────
# 내부 함수
# ──────────────────────────────────────────────

def _is_encrypted(zf: zipfile.ZipFile) -> bool:
    """암호화된 HWPX인지 확인."""
    for info in zf.infolist():
        if info.flag_bits & 0x1:  # 암호화 플래그
            return True
    return False


def _detect_namespaces(zf: zipfile.ZipFile) -> dict:
    """실제 HWPX 파일에서 네임스페이스를 감지."""
    ns = dict(DEFAULT_NS)

    # section0.xml 또는 content.xml에서 네임스페이스 추출
    for name in zf.namelist():
        if "section" in name.lower() and name.endswith(".xml"):
            xml_bytes = zf.read(name)
            xml_str = xml_bytes.decode("utf-8", errors="replace")
            # xmlns:hp="..." 패턴 탐색
            for match in re.finditer(r'xmlns:(\w+)="([^"]+)"', xml_str):
                prefix, uri = match.groups()
                ns[prefix] = uri
            break

    return ns


def _find_content_xmls(zf: zipfile.ZipFile) -> list[str]:
    """본문 XML 파일들을 찾는다. section*.xml 또는 content.xml."""
    names = zf.namelist()
    content_xmls = []

    # section 파일 우선 탐색 (section0.xml, section1.xml, ...)
    section_files = sorted(
        [n for n in names if re.search(r"[Cc]ontents/[Ss]ection\d*\.xml", n)]
    )
    if section_files:
        return section_files

    # content.xml 탐색
    content_files = [n for n in names if n.lower().endswith("content.xml")]
    if content_files:
        return content_files

    # Contents 디렉토리 내 모든 XML
    contents_xmls = [
        n for n in names
        if n.lower().startswith("contents/") and n.endswith(".xml")
        and "header" not in n.lower() and "footer" not in n.lower()
    ]
    return contents_xmls


def _parse_paragraphs(root: ET.Element, ns: dict) -> list[dict]:
    """XML에서 단락(paragraph) 목록을 추출."""
    paragraphs = []

    # <hp:p> 또는 네임스페이스 없는 <p> 탐색
    p_elements = root.findall(".//{%s}p" % ns.get("hp", ""))
    if not p_elements:
        # 네임스페이스 변형 시도
        p_elements = root.findall(".//{http://www.hancom.co.kr/hwpml/2011/paragraph}p")
    if not p_elements:
        # 모든 네임스페이스로 시도
        p_elements = _find_all_with_local_name(root, "p")

    for p in p_elements:
        text_parts = []
        # <hp:run> 내 <hp:t> 텍스트 수집
        for t in _find_all_with_local_name(p, "t"):
            if t.text:
                text_parts.append(t.text)

        text = "".join(text_parts).strip()
        if text:
            paragraphs.append({"text": text})

    return paragraphs


def _parse_tables(root: ET.Element, ns: dict) -> list[dict]:
    """XML에서 표(table) 데이터를 추출."""
    tables = []

    tbl_elements = _find_all_with_local_name(root, "tbl")

    for tbl in tbl_elements:
        rows_data = []
        tr_elements = _find_all_with_local_name(tbl, "tr")

        for tr in tr_elements:
            cells = []
            tc_elements = _find_all_with_local_name(tr, "tc")

            for tc in tc_elements:
                # 셀 내 텍스트 수집
                cell_texts = []
                for t in _find_all_with_local_name(tc, "t"):
                    if t.text:
                        cell_texts.append(t.text)
                cells.append("".join(cell_texts).strip())

            if cells:
                rows_data.append(cells)

        if rows_data:
            tables.append({"rows": rows_data})

    return tables


def _extract_images(zf: zipfile.ZipFile) -> list[dict]:
    """BinData 디렉토리에서 이미지 파일을 추출."""
    images = []
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"}

    for name in zf.namelist():
        if "BinData" in name or "bindata" in name:
            ext = Path(name).suffix.lower()
            if ext in image_exts:
                images.append({
                    "path": name,
                    "data": zf.read(name),
                })

    return images


def _parse_metadata(zf: zipfile.ZipFile) -> dict:
    """docProps에서 문서 메타데이터를 추출."""
    metadata = {}

    # core.xml 또는 app.xml 탐색
    for name in zf.namelist():
        if "docProps" in name or "docprops" in name:
            if name.endswith(".xml"):
                try:
                    xml_bytes = zf.read(name)
                    root = ET.fromstring(xml_bytes)
                    # 일반적인 메타데이터 필드
                    for elem in root:
                        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem.text and tag in ("title", "creator", "subject",
                                                  "description", "created", "modified"):
                            metadata[tag] = elem.text.strip()
                except ET.ParseError:
                    pass

    return metadata


def _find_all_with_local_name(element: ET.Element, local_name: str) -> list[ET.Element]:
    """네임스페이스에 관계없이 로컬 이름으로 요소를 찾는다."""
    results = []
    for elem in element.iter():
        tag = elem.tag
        if "}" in tag:
            tag = tag.split("}")[-1]
        if tag == local_name:
            results.append(elem)
    return results


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="HWPX 파일 파서")
    parser.add_argument("input", help="HWPX 파일 경로")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    result = parse_hwpx(args.input)

    if args.json:
        # images의 bytes 데이터는 제외
        output = {
            "text": result["text"],
            "paragraphs": result["paragraphs"],
            "tables": result["tables"],
            "images": [{"path": img["path"], "size": len(img["data"])} for img in result["images"]],
            "metadata": result["metadata"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"[메타데이터] {result['metadata']}")
        print(f"[단락 수] {len(result['paragraphs'])}")
        print(f"[표 수] {len(result['tables'])}")
        print(f"[이미지 수] {len(result['images'])}")
        print(f"\n[본문 텍스트 (처음 500자)]")
        print(result["text"][:500])
