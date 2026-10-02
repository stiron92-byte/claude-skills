# doc-automation

> 자료를 읽고, 보고 대상에 맞춘 보고 PPT·이메일을 만든다. 숫자는 모두 출처와 대조한다.
> 플러그인: `kevin-skills-book` · 책 2장

## 하는 일

PDF·Word·PPT·한글(HWPX)·엑셀/CSV·웹페이지를 출처 ID(S01…)가 붙은 텍스트로 추출하고, Claude가 대상의 관심 포인트에 답하는
스토리라인(outline.json)을 설계한다. `build_deck.py`가 편집 가능한 차트·표를 담은 PPT로 그리고, `verify_deck.py`가
슬라이드·표·차트의 모든 숫자를 출처와 대조한다. 회사 PPT 템플릿이 있으면 그 크기·레이아웃·제목 칸을 따른다.

## 데모

| 이렇게 요청하면 | 이런 결과가 나온다 |
|-----------------|--------------------|
| "이 PDF를 분석해서 과장님께 보고 드려야 해. 포인트는 1. 이번 주 달러/원 방향 2. 우리 회사 리스크. PPT로 만들어줘" | 결론→근거→리스크→대응 순서의 6~8장 PPT, 숫자 출처 표시 |
| "2장-기업PPT 폴더 자료로 팁스 지원 발표자료 만들어줘" | 회사 문서 6개 기반 소개 덱(로고 포함). 읽지 못한 공고 파일은 따로 알림 |
| "weekly_sales.csv로 팀장님 주간 보고 + 임원용 보고 메일" | KPI·추이·채널 분해 덱 + `email_executive.md` |
| "이 회사 템플릿으로 만들어줘" (+ .pptx) | 템플릿 크기·레이아웃·제목 칸을 따른 덱 |

실습 샘플: `practice-samples` 스킬로 `doc-fx-pdf`, `doc-company-ppt`, `doc-weekly-sales` 세트를 복사해서 시험한다.

## 요구사항

| 항목 | 필수 | 설치 |
|------|:---:|------|
| Python 3.10+ | ✅ | |
| python-pptx, pandas, python-docx, pdfplumber, beautifulsoup4, lxml, openpyxl | ✅ | `python -m pip install -r scripts/requirements.txt -c <저장소>/constraints.txt` |
| matplotlib | | 빠른 주간보고 모드(차트 이미지)에만 필요 |
| PowerPoint(Windows) 또는 LibreOffice | | 슬라이드 이미지 검수(`render_slides.py`) |

설치 확인: `doctor` 스킬 또는 `python scripts/_vendor/doctor.py --skills doc-automation`

## 지원 환경

| Claude Code Win | Claude Code Mac | Cowork | claude.ai |
|:-:|:-:|:-:|:-:|
| 지원 | 지원(이미지 검수는 LibreOffice 필요) | 지원(이미지 검수는 환경에 따라 생략) | 지원(업로드 시 `_vendor` 포함 필요) |

## 커스터마이즈 포인트

플러그인 설치 폴더를 고치지 말고 오버라이드 폴더에 파일을 둔다(`references/_shared/overrides.md`).
`<작업 폴더>/.claude/claude-skills/doc-automation/` 또는 `~/.claude/claude-skills/doc-automation/`

| 수준 | 대상 | 파일(스킬 폴더 기준 상대 경로) | 형식 | 예시 |
|:---:|------|-------------------------------|------|------|
| L0 | 기본 보고 대상 | `settings.yaml` → `default_audience` | 문자열 | `default_audience: 본부장` |
| L0 | 기본 최대 장수 | `settings.yaml` → `max_slides` | 정수 | `max_slides: 8` |
| L0 | 회사 글꼴 | `settings.yaml` → `font_family` | 글꼴 이름 | `font_family: Pretendard` |
| L0 | 강조색 | `settings.yaml` → `accent` | `#RRGGBB` | `accent: "#00A0E9"` |
| L0 | 회사명(표지 작성자) | `settings.yaml` → `company_name` | 문자열 | `company_name: 우리회사` |
| L1 | 회사 PPT 템플릿 | `templates/brand.pptx` | PPTX | 사내 표준 양식 |
| L1 | 이메일 양식 | `templates/email/executive.md`, `templates/email/team.md` | 마크다운 | 사내 보고 메일 형식 |
| L2 | 회사 보고서 규칙 | `references/house-style.md` | 마크다운 | 표준 목차, 금지 표현, 필수 고지 문구 |

보호 규칙(오버라이드로 바뀌지 않음): 원본 덮어쓰기 금지, 비밀 정보 파일 기록 금지, 투자 권유 금지, 외부 전송 전 확인, 이상값 자동 수정 금지.

## 데이터 흐름

| 데이터 | 외부 전송 경로 |
|--------|----------------|
| 입력 문서 텍스트 | Claude(스토리라인 설계). 추출·렌더링·검증은 로컬 |
| URL 입력 | WebFetch로 해당 페이지 조회 |

## 변경 이력

| 버전 | 변경 |
|------|------|
| 2.0.0-alpha.1 | 스토리라인 중심으로 재설계: extract_sources(출처 ID), build_deck(9종 슬라이드·네이티브 차트·회사 템플릿), verify_deck(숫자 출처 대조), render_slides(이미지 검수). 템플릿 플레이스홀더 매핑 버그 수정, 배포용 HWPX 안내. HWPX 양식 편집은 hwpx-editor로 분리 |
| 1.6.1 | 책 출간 시점(고정 5장 주간보고 파이프라인) |
