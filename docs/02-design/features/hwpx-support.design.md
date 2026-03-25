# Design: HWPX 파일 지원 (hwpx-support)

> Plan 문서: `docs/01-plan/features/hwpx-support.plan.md`

## 1. 아키텍처 개요

### 전체 흐름

```
                        ┌──────────────────┐
                        │   입력 파일       │
                        │  (.hwpx)         │
                        └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              [모드 A]      [모드 B]      [모드 C]
            HWPX → PPT    HWPX 템플릿    HWPX → 텍스트
            (기존 파이프)   (새 HWPX 생성)  (분석만)
                    │            │            │
                    ▼            ▼            ▼
            ┌────────────┐ ┌──────────┐ ┌──────────┐
            │analyze_data│ │hwpx_     │ │analysis  │
            │→create_pptx│ │template  │ │.json     │
            └────────────┘ └──────────┘ └──────────┘
                    │            │
                    ▼            ▼
              [report.pptx] [output.hwpx]
```

### 모드 설명

| 모드 | 트리거 | 설명 |
|------|--------|------|
| **A: HWPX → PPT** | `--input file.hwpx` (기본) | HWPX 텍스트 추출 → 기존 분석/PPT 파이프라인 |
| **B: HWPX 템플릿** | `--input data.csv --hwpx-template tmpl.hwpx` | 데이터를 HWPX 템플릿에 채워서 새 HWPX 생성 |
| **C: 분석만** | `python analyze_data.py --input file.hwpx` | HWPX에서 텍스트 추출 + 분석 결과만 출력 |

## 2. 모듈 상세 설계

### 2.1 `hwpx_parser.py` (신규)

HWPX 파일에서 콘텐츠를 추출하는 모듈.

```python
"""HWPX 파일 파서 — 텍스트, 표, 이미지 추출."""

# 공개 API
def parse_hwpx(file_path: str) -> dict:
    """HWPX 파일을 파싱하여 구조화된 콘텐츠를 반환.

    Returns:
        {
            "text": str,           # 전체 본문 텍스트 (단락 연결)
            "paragraphs": list,    # [{"text": str, "style": str}, ...]
            "tables": list,        # [{"rows": [[cell, ...], ...]}, ...]
            "images": list,        # [{"path": str, "data": bytes}, ...]
            "metadata": dict,      # {"title": str, "author": str, ...}
        }
    """

def extract_text(file_path: str) -> str:
    """HWPX에서 텍스트만 추출. analyze_data.py 연동용."""
```

#### 내부 구현 흐름

```
parse_hwpx(file_path)
    │
    ├─ 1. zipfile.ZipFile(file_path) 으로 열기
    │
    ├─ 2. _find_content_xml(zf)
    │     └─ Contents/content.xml 또는 Contents/section0.xml 탐색
    │
    ├─ 3. _parse_paragraphs(content_xml)
    │     ├─ 네임스페이스 등록: hp, hc, ha, ...
    │     ├─ <hp:p> 요소 순회
    │     ├─ <hp:run> 내 <hp:t> 텍스트 수집
    │     └─ paragraphs 리스트 생성
    │
    ├─ 4. _parse_tables(content_xml)
    │     ├─ <hp:tbl> 요소 탐색
    │     ├─ <hp:tr> → <hp:tc> 순회
    │     └─ 셀 텍스트를 2D 리스트로 수집
    │
    ├─ 5. _extract_images(zf)
    │     ├─ BinData/ 디렉토리 내 파일 목록
    │     └─ 이미지 파일(png, jpg, gif, bmp) 바이트 추출
    │
    └─ 6. _parse_metadata(zf)
          └─ docProps/ 에서 제목, 작성자 등 파싱
```

#### OWPML 네임스페이스 매핑

```python
HWPX_NS = {
    "hp":  "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hc":  "http://www.hancom.co.kr/hwpml/2011/core",
    "ha":  "http://www.hancom.co.kr/hwpml/2011/app",
    "hs":  "http://www.hancom.co.kr/hwpml/2011/section",
    "opc": "http://schemas.openxmlformats.org/package/2006/content-types",
}
```

> 주의: 네임스페이스 URL은 한컴 오피스 버전에 따라 다를 수 있음.
> 실제 HWPX 파일의 XML에서 확인 후 조정 필요.

### 2.2 `hwpx_template.py` (신규)

HWPX 템플릿에 데이터를 채워 새 파일을 생성하는 모듈.

```python
"""HWPX 템플릿 엔진 — 플레이스홀더 치환으로 문서 생성."""

# 공개 API
def fill_template(
    template_path: str,
    data: dict,
    output_path: str,
    placeholder_pattern: str = r"\{\{(\w+)\}\}",
) -> str:
    """HWPX 템플릿의 플레이스홀더를 데이터로 치환하여 저장.

    Args:
        template_path: HWPX 템플릿 파일 경로
        data: {"변수명": "값", ...} 딕셔너리
        output_path: 출력 HWPX 파일 경로
        placeholder_pattern: 플레이스홀더 정규식 (기본: {{변수명}})

    Returns:
        output_path
    """

def scan_placeholders(template_path: str) -> list[str]:
    """템플릿에서 모든 플레이스홀더를 찾아 변수명 리스트 반환."""
```

#### 내부 구현 흐름

```
fill_template(template_path, data, output_path)
    │
    ├─ 1. 임시 디렉토리에 ZIP 해제
    │     └─ tempfile.mkdtemp() + zipfile.extractall()
    │
    ├─ 2. XML 파일 목록 수집
    │     └─ Contents/*.xml 파일 순회
    │
    ├─ 3. 각 XML 파일에서 플레이스홀더 치환
    │     ├─ _replace_in_xml(xml_path, data, pattern)
    │     │   ├─ <hp:t> 요소의 텍스트에서 {{key}} 탐색
    │     │   ├─ data[key] 값으로 치환
    │     │   └─ 치환한 <hp:p>의 <hp:linesegarray> 제거
    │     └─ 치환 건수 기록
    │
    ├─ 4. _remove_linesegarray(paragraph_element)
    │     └─ 수정된 단락의 레이아웃 캐시 제거
    │
    └─ 5. ZIP으로 재패키징
          ├─ mimetype: 비압축(ZIP_STORED)
          └─ 나머지: 압축(ZIP_DEFLATED)
```

#### linesegarray 처리 상세

```python
def _remove_linesegarray(p_element):
    """<hp:p> 요소에서 <hp:linesegarray>를 제거.

    HWPX는 DOCX와 달리 레이아웃 캐시를 XML에 저장한다.
    텍스트를 수정한 뒤 이 캐시를 제거하지 않으면
    한컴 오피스에서 열 때 글자가 겹쳐 보인다.

    캐시는 문서를 한컴 오피스에서 열면 자동 재생성된다.
    """
    for lsa in p_element.findall(".//hp:linesegarray", HWPX_NS):
        p_element.remove(lsa)
```

#### ZIP 재패키징 규칙

```python
def _repack_hwpx(source_dir: str, output_path: str):
    """해제된 HWPX 디렉토리를 다시 ZIP으로 패키징.

    규칙:
    1. mimetype 파일은 반드시 첫 번째 엔트리, 비압축
    2. 나머지 파일은 ZIP_DEFLATED로 압축
    3. 디렉토리 구조 유지
    """
```

### 2.3 `analyze_data.py` 수정사항

#### 변경 1: HWPX를 DOCUMENT_EXTENSIONS에 추가

```python
# 변경 전
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".html", ".htm", ".md", ".txt"}

# 변경 후
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".html", ".htm", ".md", ".txt", ".hwpx"}
```

#### 변경 2: `load_document_text()` 에 HWPX 분기 추가

```python
def load_document_text(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".hwpx":
        return _load_hwpx(path)    # ← 추가
    elif ext == ".pdf":
        ...
```

#### 변경 3: `_load_hwpx()` 함수 추가

```python
def _load_hwpx(path: Path) -> str:
    """HWPX에서 텍스트를 추출합니다."""
    try:
        from hwpx_parser import extract_text
        return extract_text(str(path))
    except ImportError:
        raise ImportError(
            "HWPX 파일을 읽으려면 hwpx_parser 모듈이 필요합니다.\n"
            "chapter2-doc-automation/scripts/ 디렉토리에 hwpx_parser.py가 있는지 확인하세요."
        )
```

### 2.4 `generate_report.py` 수정사항

#### 변경: HWPX 입력 및 HWPX 템플릿 모드 지원

```python
def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="output")
    parser.add_argument("--template", default=None, help="PPT 템플릿 경로")
    parser.add_argument("--hwpx-template", default=None,     # ← 추가
                        help="HWPX 템플릿 경로 (데이터를 채워 HWPX 출력)")

    args = parser.parse_args()
    ...

    # HWPX 템플릿 모드: 데이터 → HWPX 출력
    if args.hwpx_template:
        from hwpx_template import fill_template
        # analysis 결과의 summary를 플레이스홀더 데이터로 변환
        hwpx_data = _build_hwpx_data(analysis)
        hwpx_out = str(output_dir / "report.hwpx")
        fill_template(args.hwpx_template, hwpx_data, hwpx_out)
        print(f"  HWPX 보고서: {hwpx_out}")

    # 기존 PPT 생성은 그대로 유지
    ...
```

## 3. 데이터 구조

### 3.1 parse_hwpx() 반환 구조

```json
{
  "text": "전체 본문 텍스트...",
  "paragraphs": [
    {"text": "첫 번째 단락", "style": "Normal"},
    {"text": "두 번째 단락", "style": "Heading1"}
  ],
  "tables": [
    {
      "rows": [
        ["항목", "수량", "금액"],
        ["A상품", "100", "50,000"],
        ["B상품", "200", "80,000"]
      ]
    }
  ],
  "images": [
    {"path": "BinData/image1.png", "data": "<bytes>"}
  ],
  "metadata": {
    "title": "주간 보고서",
    "author": "홍길동",
    "created": "2026-03-20"
  }
}
```

### 3.2 fill_template() 데이터 매핑

```python
# analyze_data의 분석 결과 → HWPX 플레이스홀더 매핑
hwpx_data = {
    # 테이블형 데이터인 경우
    "total_revenue": "12,500,000",
    "total_quantity": "850",
    "avg_daily_revenue": "1,785,714",
    "period_start": "2026-03-18",
    "period_end": "2026-03-24",
    "report_date": "2026-03-25",
    "change_rate": "+12.5%",

    # 문서형 데이터인 경우
    "summary_text": "핵심 내용 요약...",
    "total_sections": "5",
    "total_words": "3,200",
}
```

## 4. 에러 처리

| 상황 | 처리 |
|------|------|
| HWPX가 아닌 파일 (ZIP이 아님) | `ValueError: 유효한 HWPX 파일이 아닙니다` |
| content.xml 없음 | `ValueError: HWPX 구조가 올바르지 않습니다 (content.xml 없음)` |
| 암호화된 HWPX | `ValueError: 암호화된 HWPX 파일은 지원하지 않습니다` |
| 플레이스홀더 매칭 안됨 | 경고 출력 후 원본 텍스트 유지 |
| python-hwpx 미설치 | stdlib(zipfile + xml.etree)로 동작, 외부 의존성 불필요 |

## 5. 의존성 전략

### 외부 의존성 없음 (핵심 원칙)

```
hwpx_parser.py   → zipfile (stdlib) + xml.etree (stdlib)
hwpx_template.py → zipfile (stdlib) + xml.etree (stdlib) + re (stdlib)
```

- **python-hwpx는 사용하지 않는다** — stdlib만으로 충분하며, 외부 의존성을 최소화
- `requirements.txt` 변경 없음

## 6. 수정 대상 파일 요약

| 파일 | 작업 | 변경량 |
|------|------|--------|
| `scripts/hwpx_parser.py` | **신규** | ~150줄 |
| `scripts/hwpx_template.py` | **신규** | ~120줄 |
| `scripts/analyze_data.py` | **수정** | ~15줄 추가 |
| `scripts/generate_report.py` | **수정** | ~20줄 추가 |
| `SKILL.md` | **수정** | 지원 형식 표에 `.hwpx` 추가 |

## 7. 구현 순서

```
Step 1: hwpx_parser.py
        ├─ HWPX ZIP 구조 파싱
        ├─ 텍스트 추출 (paragraphs)
        ├─ 표 추출 (tables)
        └─ 이미지 목록 추출

Step 2: analyze_data.py 통합
        ├─ DOCUMENT_EXTENSIONS에 .hwpx 추가
        ├─ _load_hwpx() 함수 추가
        └─ 테스트: HWPX → analysis.json

Step 3: hwpx_template.py
        ├─ 플레이스홀더 스캔
        ├─ 치환 엔진
        ├─ linesegarray 제거
        └─ ZIP 재패키징

Step 4: generate_report.py 통합
        ├─ --hwpx-template 옵션 추가
        ├─ _build_hwpx_data() 매핑 함수
        └─ 테스트: CSV + HWPX 템플릿 → output.hwpx

Step 5: SKILL.md 업데이트
        └─ 지원 형식, 커맨드 예시 추가
```

## 8. 테스트 전략

### 단위 테스트

| 테스트 | 검증 항목 |
|--------|----------|
| `parse_hwpx` 기본 | 유효한 HWPX에서 text, paragraphs 추출 |
| `parse_hwpx` 표 | 표 데이터가 2D 리스트로 올바르게 추출 |
| `parse_hwpx` 에러 | 잘못된 파일, ZIP 아닌 파일 → ValueError |
| `fill_template` 기본 | `{{key}}` 치환 후 올바른 HWPX 생성 |
| `fill_template` lineseg | 치환된 단락에서 linesegarray 제거 확인 |
| `scan_placeholders` | 템플릿의 모든 플레이스홀더 목록 반환 |

### 통합 테스트

| 테스트 | 검증 항목 |
|--------|----------|
| HWPX → PPT 파이프라인 | `generate_report.py --input file.hwpx` → PPT 생성 |
| HWPX 템플릿 모드 | `--input data.csv --hwpx-template tmpl.hwpx` → HWPX 생성 |
| 기존 기능 회귀 | CSV/PDF/DOCX 입력 → 기존과 동일한 결과 |
