# Completion Report: HWPX 파일 지원 (hwpx-support)

> 완료일: 2026-03-25

## 1. 요약

| 항목 | 값 |
|------|-----|
| 기능명 | HWPX 파일 지원 |
| Match Rate | **97.7%** (42/43) |
| 반복 횟수 | 0 (첫 구현에서 통과) |
| 신규 파일 | 2개 (~390줄) |
| 수정 파일 | 3개 (~50줄 추가) |
| 외부 의존성 추가 | **0개** (stdlib만 사용) |

## 2. PDCA 진행 이력

```
[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ (97.7%) → [Report] ✅
```

| 단계 | 산출물 | 상태 |
|------|--------|------|
| Plan | `docs/01-plan/features/hwpx-support.plan.md` | ✅ |
| Design | `docs/02-design/features/hwpx-support.design.md` | ✅ |
| Do | 5개 파일 구현 | ✅ |
| Check | `docs/03-analysis/hwpx-support.analysis.md` | ✅ 97.7% |
| Report | 이 문서 | ✅ |

## 3. 구현 결과

### 신규 모듈

#### `hwpx_parser.py` (~200줄)
HWPX 파일에서 콘텐츠를 추출하는 파서.

- **parse_hwpx()** — 텍스트, 표, 이미지, 메타데이터를 구조화된 dict로 반환
- **extract_text()** — 표 포함 전체 텍스트 추출 (analyze_data.py 연동)
- ZIP 유효성 검증, 암호화 파일 거부
- OWPML 네임스페이스 동적 감지
- 네임스페이스 무관 요소 탐색 (`_find_all_with_local_name`)

#### `hwpx_template.py` (~190줄)
HWPX 템플릿에 데이터를 채워 새 문서를 생성하는 엔진.

- **fill_template()** — `{{변수명}}` 플레이스홀더를 데이터로 치환
- **scan_placeholders()** — 템플릿의 모든 플레이스홀더 목록 반환
- linesegarray 자동 제거 (글자 겹침 방지)
- mimetype 비압축 + 나머지 압축 재패키징

### 기존 모듈 수정

#### `analyze_data.py` (+15줄)
- `.hwpx`를 `DOCUMENT_EXTENSIONS`에 추가
- `_load_hwpx()` 함수로 hwpx_parser 연동
- `load_document_text()`에 `.hwpx` 분기 추가

#### `generate_report.py` (리팩토링)
- `--hwpx-template` CLI 옵션 추가
- 입력 파일의 tabular/document 자동 분기 처리
- `_build_hwpx_data()` — 분석 결과를 플레이스홀더 데이터로 매핑
- HWPX + PPT 동시 출력 지원

#### `SKILL.md`
- 지원 파일 형식에 `.hwpx` 추가
- HWPX 관련 자동 감지 상황 2개 추가
- 커맨드 예시 2개 추가
- 파일 구조에 신규 모듈 반영

## 4. 지원 모드

| 모드 | 커맨드 | 설명 |
|------|--------|------|
| HWPX → PPT | `--input file.hwpx` | HWPX 텍스트 추출 → 분석 → PPT |
| HWPX 템플릿 | `--input data.csv --hwpx-template tmpl.hwpx` | 데이터를 HWPX 양식에 채움 |
| 분석만 | `python analyze_data.py --input file.hwpx` | 텍스트 추출 + analysis.json |

## 5. 설계 갭 (미해결)

| 갭 | 영향도 | 사유 |
|----|--------|------|
| 단락 `style` 필드 | 낮음 | 하류 코드에서 미사용, 의도적 생략 |

## 6. 핵심 기술 결정

| 결정 | 근거 |
|------|------|
| python-hwpx 미사용 → stdlib만 사용 | 외부 의존성 0개 유지, stdlib로 충분 |
| 네임스페이스 동적 감지 | 한컴 오피스 버전별 차이 대응 |
| linesegarray 전체 제거 | 부분 제거보다 안전, 한컴에서 자동 재생성 |
| mimetype 비압축 패키징 | HWPX/OPC 표준 준수 |

## 7. 사용 방법

```bash
# HWPX → PPT 변환
python scripts/generate_report.py --input 보고서.hwpx --output output/

# HWPX 템플릿에 데이터 채우기
python scripts/generate_report.py --input data.csv --hwpx-template 양식.hwpx --output output/

# HWPX 파일 분석만
python scripts/analyze_data.py --input 문서.hwpx --output output/

# HWPX 파서 직접 사용
python scripts/hwpx_parser.py 문서.hwpx --json

# HWPX 템플릿 플레이스홀더 스캔
python scripts/hwpx_template.py scan 양식.hwpx

# HWPX 템플릿 채우기 (직접)
python scripts/hwpx_template.py fill 양식.hwpx --data data.json --output 결과.hwpx
```
