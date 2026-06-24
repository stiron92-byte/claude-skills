---
name: doc-automation
description: 다양한 형식의 파일(CSV, 엑셀, PDF, Word, PPT, HTML, Markdown 등)을 분석하여 주간 보고 PPT와 요약 이메일을 자동 생성합니다. 보고서 작성, PPT 생성, 데이터 분석, 문서 요약이 필요할 때 사용하세요.
---

# doc-automation — 문서·PPT 자동화 스킬

> 어떤 파일이든 던지면 → 보고용 PPT + 요약 이메일로 자동 변환

## 이 스킬이 활성화되는 상황

### 직접 호출
- 사용자가 `/doc-automation` 명령어를 입력했을 때

### 자동 감지 — 다음 상황에서 이 스킬을 사용하세요

| 상황 | 예시 대화 |
|------|----------|
| **파일 + 보고서 요청** | "이 파일로 주간 보고 만들어줘" |
| **주간/월간 보고서 요청** | "이번 주 실적 보고서 정리해줘" |
| **데이터 → PPT 변환** | "매출 데이터 분석해서 PPT로 만들어줘" |
| **문서 → PPT 변환** | "이 PDF 내용을 PPT로 정리해줘" |
| **HWPX → PPT 변환** | "이 한글 파일을 PPT로 만들어줘" |
| **HWPX 내용 변경** | "이 결재문서 양식에서 제목이랑 담당자만 바꿔줘" |
| **HWPX 템플릿 채우기** | "이 데이터를 한글 양식에 넣어줘" |
| **문서 요약 + 이메일** | "이 보고서 요약해서 팀에 공유할 이메일 써줘" |
| **보고용 이메일 작성** | "이 데이터로 임원 보고 이메일 써줘" |
| **데이터 시각화** | "매출 추이 차트 그려줘" |
| **미팅/제안서 자료** | "이 자료로 미팅용 PPT 만들어줘" |
| **기존 PPT/Word 리포맷** | "이 워드 파일을 PPT로 바꿔줘" |

### 이 스킬을 사용하지 않는 상황
- 파일 없이 처음부터 글만 작성하는 경우
- 빈 PPT 템플릿만 필요한 경우
- 코드 리뷰, 디버깅 등 개발 작업

## 지원 파일 형식

| 분류 | 확장자 | 처리 방식 |
|------|--------|----------|
| **테이블형** | `.csv`, `.xlsx`, `.xls`, `.tsv`, `.json` | 숫자 분석 → 차트 생성 → PPT |
| **문서형** | `.pdf`, `.docx`, `.doc` | 텍스트 추출 → 핵심 요약 → PPT |
| **프레젠테이션** | `.pptx`, `.ppt` | 내용 추출 → 재구성/요약 → PPT |
| **한글(HWPX)** | `.hwpx` | 텍스트/표 추출 → 요약 → PPT |
| **웹/텍스트** | `.html`, `.htm`, `.md`, `.txt` | 텍스트 파싱 → 요약 → PPT |

**테이블형 파일**: 숫자 데이터를 분석하고 차트(라인, 파이, 막대)를 자동 생성합니다.
**문서형 파일**: 텍스트를 추출·요약하고 핵심 내용을 슬라이드로 구성합니다.

## 개요

이 스킬은 파이프라인으로 보고서를 자동 생성합니다:

0. **템플릿 분석** (선택) — 회사 PPT 템플릿의 레이아웃, 테마 색상, 폰트를 자동 추출
1. **파일 분석** — 파일 형식을 자동 감지하여 데이터 분석 또는 텍스트 추출
2. **PPT 생성** — python-pptx로 템플릿 스타일에 맞춰 .pptx 파일 생성 (플레이스홀더 우선 사용)
3. **이메일 요약** — 핵심 내용을 수신자별 톤(임원용/팀원용)으로 이메일 본문 생성

## 사전 요구사항

```bash
pip install -r scripts/requirements.txt
```

필요 패키지: `python-pptx`, `pandas`, `matplotlib`, `openpyxl`, `python-docx`, `pdfplumber`, `beautifulsoup4`

## 워크플로우

### Step 0: 템플릿 분석 (선택)

사용자가 회사 PPT 템플릿을 제공하면 자동으로 분석합니다:

1. 슬라이드 크기(16:9, 4:3 등) 감지
2. 테마 색상(accent, text, background 등) 추출
3. 레이아웃(표지, 콘텐츠, 빈 슬라이드 등) 분류
4. 플레이스홀더(제목, 본문 영역) 위치 파악
5. 폰트 패밀리 추출

```bash
# 템플릿 분석만 실행
python scripts/template_analyzer.py --input 회사템플릿.pptx

# JSON으로 결과 출력
python scripts/template_analyzer.py --input 회사템플릿.pptx --json
```

### Step 1: 파일 분석

사용자가 파일을 제공하면 확장자를 자동 감지하여 처리합니다:

**테이블형 (.csv, .xlsx 등)**:
1. pandas로 데이터를 로드합니다
2. 주요 지표(합계, 평균, TOP 항목 등)를 자동 계산합니다
3. matplotlib으로 차트를 생성합니다

**문서형 (.pdf, .docx, .pptx, .html, .md 등)**:
1. 각 형식에 맞는 파서로 텍스트를 추출합니다
2. 핵심 문장, 섹션 구조, 수치 데이터를 분석합니다

```bash
python scripts/analyze_data.py --input <파일경로> --output output/
```

### Step 2: PPT 생성

분석 결과를 기반으로 PPT를 생성합니다:

1. `scripts/create_pptx.py`를 실행합니다
2. 회사 템플릿이 있으면 레이아웃/색상/폰트를 자동 적용합니다
3. 템플릿의 플레이스홀더가 있으면 거기에 내용을 삽입하고, 없으면 비율 좌표로 배치합니다
3. 5장 슬라이드 구성:
   - **표지**: 보고서 제목, 날짜, 작성자
   - **요약**: 핵심 KPI 또는 주요 내용 요약
   - **상세 분석**: 차트 또는 본문 내용
   - **주요 이슈**: 이슈 및 액션 아이템
   - **다음 주 계획**: 목표 및 일정

```bash
python scripts/create_pptx.py --analysis output/analysis.json --output output/weekly_report.pptx
```

### Step 3: 이메일 요약

핵심 내용을 이메일 본문으로 변환합니다:

- **임원용**: 핵심 수치 + 결론 중심, 간결체
- **팀원용**: 상세 데이터 + 액션 아이템 포함

```bash
python scripts/generate_email.py --analysis output/analysis.json --type both
```

### 전체 실행

위 단계를 한 번에 실행합니다:

```bash
# 기본 실행
python scripts/generate_report.py --input <파일경로> --output output/

# 회사 PPT 템플릿 적용
python scripts/generate_report.py --input <파일경로> --template 회사템플릿.pptx --output output/

# HWPX 파일 → PPT 변환
python scripts/generate_report.py --input 보고서.hwpx --output output/

# HWPX 템플릿에 데이터 채우기
python scripts/generate_report.py --input data.csv --hwpx-template 양식.hwpx --output output/
```

## 샘플 데이터로 실습

```bash
python scripts/generate_report.py --input samples/weekly_sales.csv --output output/
```

실행 결과:
- `output/weekly_report.pptx` — 5장짜리 주간 보고 PPT
- `output/charts/` — 생성된 차트 이미지들 (테이블형 입력 시)
- `output/analysis.json` — 분석 결과 데이터
- `output/extracted_text.txt` — 추출된 텍스트 (문서형 입력 시)
- `output/email_executive.md` — 임원용 요약 이메일
- `output/email_team.md` — 팀원용 상세 이메일

## HWPX 문서 내용 변경 (핵심 기능)

기존 HWPX 문서의 양식(레이아웃, 로고, 서체, 테이블 구조)을 그대로 유지하면서
텍스트 내용만 교체합니다.

**절대 주의**: XML 파서(ElementTree 등)를 사용하면 안 됩니다.
반드시 `hwpx_template.py`의 `replace_texts()` 함수를 사용하거나,
직접 구현할 때도 순수 문자열 치환(str.replace)만 사용하세요.
XML 파서는 네임스페이스를 변환하여 한컴 오피스에서 파일이 깨집니다.

### 방법 1: Python 코드에서 직접 호출 (권장)

```python
from hwpx_template import replace_texts

replace_texts(
    "원본문서.hwpx",
    [
        ("원본 제목", "새 제목"),
        ("원본 담당자", "새 담당자"),
        ("원본 본문 내용", "새 본문 내용"),
    ],
    "output/결과문서.hwpx",
)
```

### 방법 2: CLI로 실행

```bash
# 1단계: 원본 HWPX의 텍스트 확인
python scripts/hwpx_template.py extract 원본문서.hwpx

# 2단계: 치환 맵 JSON 작성
cat > replacements.json << 'EOF'
{
    "원본 제목": "새 제목",
    "원본 담당자": "새 담당자",
    "원본 본문": "새 본문"
}
EOF

# 3단계: 치환 실행
python scripts/hwpx_template.py replace 원본문서.hwpx --map replacements.json --output output/결과.hwpx
```

### 방법 3: AI가 직접 Python 스크립트 작성

사용자가 HWPX 파일과 변경 내용을 알려주면, 아래 패턴으로 스크립트를 작성하세요:

```python
import re, zipfile

SRC = "원본.hwpx"
DST = "output/결과.hwpx"

REPLACEMENTS = [
    ("원본텍스트1", "새텍스트1"),
    ("원본텍스트2", "새텍스트2"),
]

with zipfile.ZipFile(SRC, "r") as zf_in:
    with zipfile.ZipFile(DST, "w") as zf_out:
        for name in zf_in.namelist():
            data = zf_in.read(name)
            info = zf_in.getinfo(name)
            compress = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED

            if name.endswith(".xml"):
                xml_str = data.decode("utf-8")
                for old, new in REPLACEMENTS:
                    xml_str = xml_str.replace(old, new)
                # linesegarray 제거 (한컴에서 자동 재생성)
                xml_str = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", xml_str, flags=re.DOTALL)
                data = xml_str.encode("utf-8")

            zf_out.writestr(info, data, compress_type=compress)
```

**주의사항**:
- 원본 텍스트를 정확히 일치시켜야 합니다 (공백 포함)
- `extract_texts()` 또는 `hwpx_parser.py`로 원본 텍스트를 먼저 확인하세요
- XML 태그(`<hp:t>`, `<hp:run>` 등)는 절대 건드리지 마세요
- linesegarray는 반드시 제거해야 글자 겹침이 방지됩니다

## 커스텀 가이드

### 유튜버: 주간 채널 성과 보고서
- CSV 컬럼: 날짜, 영상제목, 조회수, 좋아요, 구독자변화

### 쇼핑몰 운영: 주간 매출 보고서
- CSV 컬럼: 날짜, 상품명, 매출, 판매량, 재고, 반품수

### 프리랜서: 월간 프로젝트 보고서
- CSV 컬럼: 클라이언트, 프로젝트명, 진행률, 투입시간, 마감일

### 기존 문서 리포맷
- PDF/Word/PPT 파일 → 내용 추출 → 새로운 보고서 PPT + 요약 이메일

## 파일 구조

```
doc-automation/
├── SKILL.md                           # 스킬 정의 파일
├── scripts/
│   ├── generate_report.py             # 전체 파이프라인 실행
│   ├── analyze_data.py                # 파일 분석 (테이블+문서+HWPX 지원)
│   ├── hwpx_parser.py                # HWPX 파일 파서 (텍스트/표/이미지 추출)
│   ├── hwpx_template.py              # HWPX 텍스트 치환 (replace_texts + fill_template)
│   ├── create_pptx.py                 # PPT 생성 (StyleConfig 기반)
│   ├── style_config.py               # 색상/폰트/좌표 설정 클래스
│   ├── template_analyzer.py          # 회사 PPT 템플릿 분석
│   ├── generate_email.py              # 이메일 요약 생성
│   ├── create_brand_template.py       # 브랜드 PPT 템플릿 생성
│   └── requirements.txt               # Python 의존성
├── samples/
│   ├── weekly_sales.csv               # 샘플 데이터
│   ├── template_16x9.pptx            # 16:9 샘플 템플릿
│   └── template_4x3.pptx             # 4:3 샘플 템플릿
├── templates/
│   └── email/
│       ├── executive.md               # 임원용 이메일 템플릿
│       └── team.md                    # 팀원용 이메일 템플릿
└── README.md
```
