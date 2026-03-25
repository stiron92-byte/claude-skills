# Plan: HWPX 파일 지원 (hwpx-support)

## 1. 배경 및 목적

### 현재 상황
chapter2-doc-automation은 CSV, PDF, Word, PPT, HTML, Markdown 등 다양한 형식을 지원하지만, 한국에서 가장 많이 사용되는 문서 형식인 **HWPX(한컴 오피스 한글)를 지원하지 않는다.**

### 목적
HWPX 파일을 두 가지 방향으로 지원한다:

1. **HWPX → PPT 변환**: HWPX 문서의 내용을 추출하여 기존 파이프라인(분석 → PPT 생성 → 이메일)에 통합
2. **HWPX 템플릿 기반 생성**: HWPX 양식을 템플릿으로 사용하여 데이터를 채워넣은 새 HWPX 문서를 생성

## 2. 요구사항

### 필수 요구사항 (Must Have)

| ID | 요구사항 | 설명 |
|----|---------|------|
| R1 | HWPX 텍스트 추출 | HWPX 파일에서 본문 텍스트, 표, 이미지 경로를 추출 |
| R2 | 기존 파이프라인 통합 | 추출된 HWPX 콘텐츠를 `analyze_data.py` → `create_pptx.py` 흐름에 연결 |
| R3 | HWPX 템플릿 읽기 | HWPX 파일을 템플릿으로 열어 플레이스홀더(예: `{{변수명}}`) 위치 파악 |
| R4 | HWPX 템플릿 채우기 | 플레이스홀더를 데이터로 치환하여 새 HWPX 파일로 저장 |
| R5 | linesegarray 처리 | 텍스트 수정 시 레이아웃 캐시(`<hp:linesegarray>`)를 제거하여 글자 겹침 방지 |
| R6 | 하위 호환성 | HWPX 관련 라이브러리 없어도 기존 기능은 정상 동작 |

### 선택 요구사항 (Nice to Have)

| ID | 요구사항 | 설명 |
|----|---------|------|
| N1 | HWPX 표 → PPT 표 변환 | HWPX 내 표를 PPT 표로 직접 변환 (서식 유지) |
| N2 | HWPX 이미지 추출 | BinData 폴더의 이미지를 추출하여 PPT 슬라이드에 삽입 |
| N3 | HWP(구 바이너리) 지원 | pyhwp 라이브러리로 레거시 HWP v5 형식도 지원 |

## 3. 범위

### In Scope
- HWPX 파서 모듈 신규 개발 (`scripts/hwpx_parser.py`)
- HWPX 템플릿 엔진 모듈 신규 개발 (`scripts/hwpx_template.py`)
- `analyze_data.py`에 HWPX 파일 형식 추가
- `SKILL.md` 지원 형식 목록에 HWPX 추가
- `requirements.txt`에 의존성 추가

### Out of Scope
- 암호화된 HWPX 파일 처리 (python-hwpx 미지원)
- HWPX 내 OLE 객체(엑셀 차트 등) 처리
- PPT → HWPX 역변환
- 한컴 HWP SDK (유료 라이선스) 사용

## 4. 기술 접근 방식

### HWPX 파일 구조 이해

HWPX는 ZIP + XML 구조로 DOCX/PPTX와 유사하다:

```
HWPX 파일 (ZIP)
├── [Content_Types].xml
├── Contents/
│   ├── content.xml        ← 본문 (단락, 표, 텍스트)
│   ├── header*.xml        ← 머리글
│   ├── footer*.xml        ← 바닥글
│   └── section*.xml       ← 섹션 구조
├── BinData/               ← 이미지, OLE 객체
├── docProps/               ← 문서 메타데이터
└── mimetype
```

### 기능 1: HWPX → PPT 변환 흐름

```
[HWPX 파일]
     │
     ▼
┌──────────────────┐
│  hwpx_parser.py  │  ← 신규 모듈
│  - ZIP 해제       │
│  - content.xml 파싱│
│  - 텍스트/표 추출  │
│  - 이미지 경로 추출│
└──────────────────┘
     │
     ▼  ExtractedContent (dict)
┌──────────────────┐
│  analyze_data.py │  ← 기존 모듈 수정
│  (문서형 분기 추가) │
└──────────────────┘
     │
     ▼  analysis.json
┌──────────────────┐
│  create_pptx.py  │  ← 기존 모듈 (변경 없음)
└──────────────────┘
     │
     ▼
[보고서.pptx]
```

### 기능 2: HWPX 템플릿 기반 생성 흐름

```
[HWPX 템플릿] + [데이터 (CSV/JSON/dict)]
     │                │
     ▼                ▼
┌────────────────────────┐
│   hwpx_template.py     │  ← 신규 모듈
│   1. ZIP 해제           │
│   2. content.xml 파싱   │
│   3. {{플레이스홀더}} 탐색│
│   4. 데이터로 치환       │
│   5. linesegarray 제거  │
│   6. ZIP으로 재패키징    │
└────────────────────────┘
     │
     ▼
[완성된.hwpx]
```

### 핵심 기술 포인트

1. **XML 파싱**: `xml.etree.ElementTree`로 OWPML 네임스페이스 처리
   - 네임스페이스: `hp` (본문), `hc` (공통), `ha` (속성)
2. **linesegarray 제거**: 텍스트 수정한 `<hp:p>` 요소에서 `<hp:linesegarray>` 삭제 필수
3. **ZIP 재패키징**: `mimetype`은 비압축, 나머지는 압축으로 저장
4. **python-hwpx 활용 검토**: 고수준 API가 있으면 활용, 없으면 직접 XML 조작

### 의존성

| 패키지 | 용도 | 필수 여부 |
|--------|------|-----------|
| `python-hwpx` | HWPX 고수준 API (읽기/쓰기) | 선택 (없으면 stdlib로 대체) |
| `zipfile` (stdlib) | HWPX ZIP 해제/생성 | 필수 (내장) |
| `xml.etree` (stdlib) | XML 파싱/수정 | 필수 (내장) |

## 5. 수정 대상 파일

| 파일 | 작업 | 설명 |
|------|------|------|
| `scripts/hwpx_parser.py` | **신규** | HWPX 파일에서 텍스트, 표, 이미지 추출 |
| `scripts/hwpx_template.py` | **신규** | HWPX 템플릿 플레이스홀더 치환 및 새 파일 생성 |
| `scripts/analyze_data.py` | **수정** | `.hwpx` 확장자 분기 추가, hwpx_parser 호출 |
| `scripts/generate_report.py` | **수정** | HWPX 입력 시 분기 처리 (PPT 변환 or HWPX 템플릿) |
| `scripts/requirements.txt` | **수정** | `python-hwpx` 추가 (선택적 의존성) |
| `SKILL.md` | **수정** | 지원 파일 형식에 `.hwpx` 추가 |

## 6. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| python-hwpx 라이브러리 불안정 | API 변경이나 버그 가능성 | stdlib(zipfile + xml.etree)로 fallback 구현 |
| HWPX 버전별 XML 구조 차이 | 한컴 오피스 버전에 따라 XML 구조가 다를 수 있음 | 주요 버전(2020, 2022, 2024) 테스트 |
| linesegarray 처리 누락 | 글자 겹침, 렌더링 깨짐 | 텍스트 수정 시 반드시 제거하는 유틸 함수 제공 |
| 복잡한 표/서식 손실 | 셀 병합, 글머리 기호 등이 PPT 변환 시 손실 가능 | 텍스트 위주 추출, 복잡 서식은 경고 출력 |
| 암호화된 HWPX | 읽기 불가 | 오류 메시지 출력 후 skip |

## 7. 성공 기준

- [ ] `.hwpx` 파일을 입력하면 텍스트를 추출하여 PPT 보고서가 생성됨
- [ ] HWPX 내 표 데이터가 분석 결과에 포함됨
- [ ] HWPX 템플릿에 `{{변수명}}` 플레이스홀더를 넣으면 데이터로 치환된 새 HWPX가 생성됨
- [ ] linesegarray 제거가 자동으로 처리되어 출력 HWPX에서 글자 겹침 없음
- [ ] 기존 파일 형식(CSV, PDF, DOCX 등) 처리에 영향 없음
- [ ] python-hwpx 미설치 환경에서도 기존 기능은 정상 동작

## 8. 구현 순서

1. **Phase 1**: `hwpx_parser.py` — 텍스트/표 추출 (핵심)
2. **Phase 2**: `analyze_data.py` 통합 — 기존 파이프라인에 HWPX 입력 연결
3. **Phase 3**: `hwpx_template.py` — 플레이스홀더 치환 엔진
4. **Phase 4**: `generate_report.py` 통합 — HWPX 템플릿 모드 추가
5. **Phase 5**: 테스트 및 SKILL.md 업데이트
