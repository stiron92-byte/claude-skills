# doc-automation — 문서·PPT 자동화 스킬

> 어떤 파일이든 던지면 → 보고용 PPT + 요약 이메일이 자동 완성됩니다.

## 지원 파일 형식

| 분류 | 확장자 | 처리 방식 |
|------|--------|----------|
| **테이블형** | `.csv` `.xlsx` `.xls` `.tsv` `.json` | 숫자 분석 → 차트 생성 → PPT |
| **문서형** | `.pdf` `.docx` `.doc` | 텍스트 추출 → 핵심 요약 → PPT |
| **프레젠테이션** | `.pptx` `.ppt` | 내용 추출 → 재구성 → PPT |
| **웹/텍스트** | `.html` `.htm` `.md` `.txt` | 텍스트 파싱 → 요약 → PPT |

## 빠른 시작

### 1. 의존성 설치

```bash
pip install -r scripts/requirements.txt
```

### 2. 샘플 데이터로 실행

```bash
cd scripts
python generate_report.py --input ../samples/weekly_sales.csv --output ../output/
```

### 3. 결과 확인

```
output/
├── weekly_report.pptx     ← 5장짜리 주간 보고 PPT
├── charts/                ← 자동 생성된 차트 이미지 (테이블형 입력 시)
├── analysis.json          ← 분석 결과 데이터
├── extracted_text.txt     ← 추출된 텍스트 (문서형 입력 시)
├── email_executive.md     ← 임원용 요약 이메일
└── email_team.md          ← 팀원용 상세 이메일
```

## 기능

| 단계 | 기능 | 설명 |
|------|------|------|
| Step 1 | 파일 분석 | 확장자 자동 감지 → 테이블 분석 또는 텍스트 추출 |
| Step 2 | PPT 생성 | python-pptx → 5장 슬라이드 (표지, KPI, 차트, 이슈, 계획) |
| Step 3 | 이메일 요약 | 수신자별 톤 변환 (임원용 간결체 / 팀원용 상세) |

## 스크립트별 실행

```bash
# 파일 분석만 (테이블형/문서형 자동 감지)
python scripts/analyze_data.py --input data.pdf --output output/

# PPT 생성만
python scripts/create_pptx.py --analysis output/analysis.json --output output/report.pptx

# 이메일만
python scripts/generate_email.py --analysis output/analysis.json --type both

# 브랜드 템플릿 생성
python scripts/create_brand_template.py --company "내 회사" --primary "3498DB"
```

## 브랜드 템플릿 커스텀

```bash
python scripts/create_brand_template.py \
  --company "ABC Corp" \
  --primary "FF6B35" \
  --secondary "004E89" \
  --output templates/brand_template.pptx
```

## 커스텀 활용 예시

- **유튜버**: 조회수·구독자·인기 영상 분석 → 주간 채널 성과 보고서
- **쇼핑몰**: 매출·재고·반품률 분석 → 주간 운영 보고서
- **프리랜서**: 클라이언트별 진행 현황 → 월간 프로젝트 보고서
- **기존 문서 리포맷**: PDF/Word 보고서 → 보고용 PPT로 재구성

## 테이블형 데이터 형식

CSV/엑셀 파일에 다음 컬럼이 포함되면 차트가 자동 생성됩니다:

| 필수 컬럼 | 설명 |
|-----------|------|
| `날짜` | 날짜 (YYYY-MM-DD) |
| `상품명` | 상품/항목 이름 |
| `매출` | 매출액 (숫자) |
| `판매량` | 판매 수량 (숫자) |

| 선택 컬럼 | 설명 |
|-----------|------|
| `카테고리` | 상품 카테고리 (파이 차트 생성) |
| `재고` | 현재 재고 수량 |
| `반품수` | 반품 수량 |

> 위 컬럼이 없는 테이블도 숫자 컬럼 기반으로 자동 분석됩니다.

## 파일 구조

```
doc-automation/
├── SKILL.md                           # 스킬 정의 (YAML 프론트매터 포함)
├── scripts/
│   ├── generate_report.py             # 전체 파이프라인
│   ├── analyze_data.py                # 파일 분석 (테이블+문서 모두 지원)
│   ├── create_pptx.py                 # PPT 생성
│   ├── generate_email.py              # 이메일 요약
│   ├── create_brand_template.py       # 브랜드 템플릿 생성
│   └── requirements.txt               # Python 의존성
├── samples/
│   └── weekly_sales.csv               # 샘플 데이터 (7일 x 7상품)
├── templates/email/
│   ├── executive.md                   # 임원용 이메일 가이드
│   └── team.md                        # 팀원용 이메일 가이드
└── README.md
```
