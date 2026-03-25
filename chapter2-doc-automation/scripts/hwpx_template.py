#!/usr/bin/env python3
"""HWPX 템플릿 엔진 — 플레이스홀더 치환으로 문서 생성.

HWPX 템플릿 파일에서 {{변수명}} 형태의 플레이스홀더를 찾아
데이터로 치환한 뒤 새 HWPX 파일로 저장한다.

핵심 원칙: XML 파서를 사용하지 않고 순수 문자열 치환만 수행한다.
ElementTree 등의 XML 파서는 네임스페이스 접두사를 변경하여
한컴 오피스에서 파일을 열 수 없게 만든다.

외부 의존성 없이 stdlib(zipfile + re)만 사용한다.
"""

import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


# 기본 플레이스홀더 패턴: {{변수명}}
DEFAULT_PATTERN = r"\{\{(\w+)\}\}"

# linesegarray 제거용 정규식 (네임스페이스 포함)
# <hp:linesegarray>...</hp:linesegarray> 또는 <linesegarray>...</linesegarray>
LINESEG_PATTERN = re.compile(
    r"<[^>]*:?linesegarray[^>]*>.*?</[^>]*:?linesegarray>",
    re.DOTALL,
)


def fill_template(
    template_path: str,
    data: dict,
    output_path: str,
    placeholder_pattern: str = DEFAULT_PATTERN,
) -> str:
    """HWPX 템플릿의 플레이스홀더를 데이터로 치환하여 저장.

    XML 파서를 사용하지 않고 순수 문자열 치환으로 처리하여
    원본 XML 구조(네임스페이스, 인코딩, 속성 순서 등)를 완벽히 보존한다.

    Args:
        template_path: HWPX 템플릿 파일 경로
        data: {"변수명": "값", ...} 딕셔너리
        output_path: 출력 HWPX 파일 경로
        placeholder_pattern: 플레이스홀더 정규식 (기본: {{변수명}})

    Returns:
        output_path

    Raises:
        ValueError: 유효한 HWPX 파일이 아닌 경우
        FileNotFoundError: 템플릿 파일이 없는 경우
    """
    if not Path(template_path).exists():
        raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {template_path}")

    if not zipfile.is_zipfile(template_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다: {template_path}")

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    replaced_count = 0
    pattern = re.compile(placeholder_pattern)

    with zipfile.ZipFile(template_path, "r") as zf_in:
        # 원본 ZIP의 파일 목록과 순서를 보존
        name_list = zf_in.namelist()

        with zipfile.ZipFile(output_path, "w") as zf_out:
            for name in name_list:
                file_bytes = zf_in.read(name)
                info = zf_in.getinfo(name)

                # mimetype은 반드시 비압축
                if name == "mimetype":
                    compress = zipfile.ZIP_STORED
                else:
                    compress = zipfile.ZIP_DEFLATED

                # XML 파일만 치환 대상
                if name.endswith(".xml"):
                    try:
                        xml_str = file_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        # UTF-8이 아닌 XML은 건드리지 않음
                        zf_out.writestr(info, file_bytes, compress_type=compress)
                        continue

                    modified = False
                    # 플레이스홀더 치환
                    for match in pattern.finditer(xml_str):
                        var_name = match.group(1)
                        if var_name in data:
                            xml_str = xml_str.replace(
                                match.group(0),
                                _escape_xml(str(data[var_name])),
                            )
                            replaced_count += 1
                            modified = True

                    # 수정된 XML에서 linesegarray 제거
                    if modified:
                        xml_str = LINESEG_PATTERN.sub("", xml_str)

                    file_bytes = xml_str.encode("utf-8")

                zf_out.writestr(info, file_bytes, compress_type=compress)

    if replaced_count == 0:
        print(f"  경고: 플레이스홀더를 찾지 못했습니다 (패턴: {placeholder_pattern})")
    else:
        print(f"  HWPX 생성 완료: {output_path} ({replaced_count}개 플레이스홀더 치환)")

    return output_path


def scan_placeholders(
    template_path: str,
    placeholder_pattern: str = DEFAULT_PATTERN,
) -> list[str]:
    """템플릿에서 모든 플레이스홀더를 찾아 변수명 리스트 반환.

    Args:
        template_path: HWPX 템플릿 파일 경로
        placeholder_pattern: 플레이스홀더 정규식

    Returns:
        ["변수명1", "변수명2", ...] (중복 제거, 등장 순서 유지)
    """
    if not zipfile.is_zipfile(template_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다: {template_path}")

    placeholders = []
    seen = set()

    with zipfile.ZipFile(template_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".xml"):
                xml_bytes = zf.read(name)
                xml_str = xml_bytes.decode("utf-8", errors="replace")
                for match in re.finditer(placeholder_pattern, xml_str):
                    var_name = match.group(1)
                    if var_name not in seen:
                        seen.add(var_name)
                        placeholders.append(var_name)

    return placeholders


# ──────────────────────────────────────────────
# 내부 함수
# ──────────────────────────────────────────────

def _escape_xml(text: str) -> str:
    """XML 특수문자를 이스케이프."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HWPX 템플릿 엔진")
    sub = parser.add_subparsers(dest="command")

    # scan 명령
    scan_parser = sub.add_parser("scan", help="플레이스홀더 스캔")
    scan_parser.add_argument("template", help="HWPX 템플릿 경로")

    # fill 명령
    fill_parser = sub.add_parser("fill", help="플레이스홀더 치환")
    fill_parser.add_argument("template", help="HWPX 템플릿 경로")
    fill_parser.add_argument("--output", required=True, help="출력 파일 경로")
    fill_parser.add_argument("--data", required=True, help="JSON 데이터 파일 경로")

    args = parser.parse_args()

    if args.command == "scan":
        placeholders = scan_placeholders(args.template)
        print(f"플레이스홀더 {len(placeholders)}개 발견:")
        for name in placeholders:
            print(f"  - {{{{{name}}}}}")

    elif args.command == "fill":
        import json
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
        fill_template(args.template, data, args.output)

    else:
        parser.print_help()
