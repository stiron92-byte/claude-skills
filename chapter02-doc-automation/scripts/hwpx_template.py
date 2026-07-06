#!/usr/bin/env python3
"""HWPX 문서 텍스트 치환 엔진.

두 가지 모드를 지원한다:

1. 직접 치환 (replace_texts): 원본 텍스트 → 새 텍스트 직접 교체
   - 기존 HWPX 문서의 내용을 바꿀 때 사용
   - 예: 결재문서의 제목, 담당자, 본문 내용 변경

2. 플레이스홀더 치환 (fill_template): {{변수명}} 패턴 치환
   - 미리 {{변수명}}을 넣어둔 양식용 HWPX에서 사용

핵심 원칙: XML 파서를 절대 사용하지 않는다.
ElementTree 등의 XML 파서는 네임스페이스 접두사(hp:, hc: 등)를
ns0, ns1 등으로 변환하여 한컴 오피스에서 파일을 열 수 없게 만든다.
반드시 순수 문자열 치환만 수행하여 원본 XML 구조를 완벽히 보존한다.

외부 의존성 없이 stdlib(zipfile + re)만 사용한다.
"""

import re
import zipfile
from pathlib import Path


# 기본 플레이스홀더 패턴: {{변수명}}
DEFAULT_PATTERN = r"\{\{(\w+)\}\}"

# linesegarray 제거용 정규식
LINESEG_PATTERN = re.compile(
    r"<[^>]*:?linesegarray[^>]*>.*?</[^>]*:?linesegarray>",
    re.DOTALL,
)


def replace_texts(
    hwpx_path: str,
    replacements: list[tuple[str, str]],
    output_path: str,
) -> str:
    """HWPX 파일의 텍스트를 직접 치환하여 새 파일로 저장.

    기존 HWPX 문서의 양식(레이아웃, 로고, 서체, 테이블 구조 등)을
    그대로 유지하면서 텍스트 내용만 교체한다.

    주의: XML 파서를 사용하지 않고 순수 문자열 치환(str.replace)으로
    처리하므로 원본 XML 구조가 완벽히 보존된다.

    Args:
        hwpx_path: 원본 HWPX 파일 경로
        replacements: [(원본텍스트, 새텍스트), ...] 치환 쌍 리스트
        output_path: 출력 HWPX 파일 경로

    Returns:
        output_path

    Example:
        replace_texts(
            "결재문서.hwpx",
            [
                ("보고서 작성 서식 안내", "2026 불꽃축제 결과보고"),
                ("서울대공원", "서울시 문화본부"),
                ("강준민", "Sol"),
            ],
            "output/불꽃축제_결과보고.hwpx",
        )
    """
    if not Path(hwpx_path).exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {hwpx_path}")

    if not zipfile.is_zipfile(hwpx_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다: {hwpx_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    replaced_count = 0

    with zipfile.ZipFile(hwpx_path, "r") as zf_in:
        with zipfile.ZipFile(output_path, "w") as zf_out:
            for name in zf_in.namelist():
                file_bytes = zf_in.read(name)
                info = zf_in.getinfo(name)
                compress = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED

                if name.endswith(".xml"):
                    try:
                        xml_str = file_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        zf_out.writestr(info, file_bytes, compress_type=compress)
                        continue

                    modified = False
                    for old_text, new_text in replacements:
                        if old_text in xml_str:
                            xml_str = xml_str.replace(old_text, new_text)
                            replaced_count += 1
                            modified = True

                    # 수정된 XML에서 linesegarray 제거 (레이아웃 캐시 — 한컴에서 자동 재생성)
                    if modified:
                        xml_str = LINESEG_PATTERN.sub("", xml_str)

                    file_bytes = xml_str.encode("utf-8")

                zf_out.writestr(info, file_bytes, compress_type=compress)

    print(f"  HWPX 생성 완료: {output_path} ({replaced_count}건 치환)")
    return output_path


def fill_template(
    template_path: str,
    data: dict,
    output_path: str,
    placeholder_pattern: str = DEFAULT_PATTERN,
) -> str:
    """HWPX 템플릿의 {{변수명}} 플레이스홀더를 데이터로 치환하여 저장.

    미리 {{변수명}} 형태의 플레이스홀더를 넣어둔 HWPX 양식 전용.
    일반 HWPX 문서의 텍스트를 바꾸려면 replace_texts()를 사용하세요.

    Args:
        template_path: HWPX 템플릿 파일 경로
        data: {"변수명": "값", ...} 딕셔너리
        output_path: 출력 HWPX 파일 경로
        placeholder_pattern: 플레이스홀더 정규식 (기본: {{변수명}})

    Returns:
        output_path
    """
    if not Path(template_path).exists():
        raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {template_path}")

    if not zipfile.is_zipfile(template_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다: {template_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    replaced_count = 0
    pattern = re.compile(placeholder_pattern)

    with zipfile.ZipFile(template_path, "r") as zf_in:
        with zipfile.ZipFile(output_path, "w") as zf_out:
            for name in zf_in.namelist():
                file_bytes = zf_in.read(name)
                info = zf_in.getinfo(name)
                compress = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED

                if name.endswith(".xml"):
                    try:
                        xml_str = file_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        zf_out.writestr(info, file_bytes, compress_type=compress)
                        continue

                    modified = False
                    for match in pattern.finditer(xml_str):
                        var_name = match.group(1)
                        if var_name in data:
                            xml_str = xml_str.replace(
                                match.group(0),
                                _escape_xml(str(data[var_name])),
                            )
                            replaced_count += 1
                            modified = True

                    if modified:
                        xml_str = LINESEG_PATTERN.sub("", xml_str)

                    file_bytes = xml_str.encode("utf-8")

                zf_out.writestr(info, file_bytes, compress_type=compress)

    if replaced_count == 0:
        print(f"  경고: 플레이스홀더를 찾지 못했습니다 (패턴: {placeholder_pattern})")
    else:
        print(f"  HWPX 생성 완료: {output_path} ({replaced_count}개 플레이스홀더 치환)")

    return output_path


def extract_texts(hwpx_path: str) -> list[str]:
    """HWPX 파일에서 모든 <hp:t> 텍스트를 추출하여 리스트로 반환.

    원본 HWPX의 텍스트를 확인하여 replace_texts()에 넘길
    치환 쌍을 준비할 때 사용한다.

    Args:
        hwpx_path: HWPX 파일 경로

    Returns:
        텍스트 리스트 (빈 문자열 제외)
    """
    if not zipfile.is_zipfile(hwpx_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다: {hwpx_path}")

    texts = []
    with zipfile.ZipFile(hwpx_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".xml"):
                xml_str = zf.read(name).decode("utf-8", errors="replace")
                for match in re.finditer(r"<hp:t>(.*?)</hp:t>", xml_str):
                    t = match.group(1).strip()
                    if t:
                        texts.append(t)
    return texts


def scan_placeholders(
    template_path: str,
    placeholder_pattern: str = DEFAULT_PATTERN,
) -> list[str]:
    """템플릿에서 모든 {{변수명}} 플레이스홀더를 찾아 변수명 리스트 반환."""
    if not zipfile.is_zipfile(template_path):
        raise ValueError(f"유효한 HWPX 파일이 아닙니다: {template_path}")

    placeholders = []
    seen = set()

    with zipfile.ZipFile(template_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".xml"):
                xml_str = zf.read(name).decode("utf-8", errors="replace")
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
    import json

    parser = argparse.ArgumentParser(description="HWPX 문서 텍스트 치환 엔진")
    sub = parser.add_subparsers(dest="command")

    # extract: 텍스트 추출
    ext_parser = sub.add_parser("extract", help="HWPX 텍스트 추출")
    ext_parser.add_argument("input", help="HWPX 파일 경로")

    # replace: 직접 치환
    rep_parser = sub.add_parser("replace", help="텍스트 직접 치환")
    rep_parser.add_argument("input", help="원본 HWPX 파일 경로")
    rep_parser.add_argument("--output", required=True, help="출력 파일 경로")
    rep_parser.add_argument("--map", required=True, help="치환 맵 JSON 파일 (키=원본, 값=새텍스트)")

    # scan: 플레이스홀더 스캔
    scan_parser = sub.add_parser("scan", help="플레이스홀더 스캔")
    scan_parser.add_argument("input", help="HWPX 템플릿 경로")

    # fill: 플레이스홀더 치환
    fill_parser = sub.add_parser("fill", help="플레이스홀더 치환")
    fill_parser.add_argument("input", help="HWPX 템플릿 경로")
    fill_parser.add_argument("--output", required=True, help="출력 파일 경로")
    fill_parser.add_argument("--data", required=True, help="JSON 데이터 파일")

    args = parser.parse_args()

    if args.command == "extract":
        texts = extract_texts(args.input)
        for i, t in enumerate(texts):
            print(f"{i:3d}: {t}")

    elif args.command == "replace":
        with open(args.map, encoding="utf-8") as f:
            mapping = json.load(f)
        pairs = list(mapping.items())
        replace_texts(args.input, pairs, args.output)

    elif args.command == "scan":
        placeholders = scan_placeholders(args.input)
        print(f"플레이스홀더 {len(placeholders)}개:")
        for name in placeholders:
            print(f"  - {{{{{name}}}}}")

    elif args.command == "fill":
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
        fill_template(args.input, data, args.output)

    else:
        parser.print_help()
