# excel-automation

> 엑셀·CSV를 정리·분석·취합한다. 원본은 그대로 두고, 모든 변경을 기록하고, 결과를 원본과 대조해 검증한다.
> 플러그인: `kevin-skills-book` · 책 3장

## 하는 일

`excel_profile.py`가 시트 구조와 열 의미를 파악하면 Claude가 필요한 기능을 고른다.

- **정리:** `clean_data.py`가 완전 중복 제거와 전화번호·날짜 형식 통일을 한다. 이메일 오타, 극단값, 모호한 날짜, 유사 중복, 빈 칸은 고치지 않고 후보 시트로 보고한다.
- **분석:** `analysis_tools.py`가 요약 통계, 월별 추이, 항목별 비교를 만든다. 엑셀 기본 차트, 히트맵 서식, 근거 셀이 붙은 인사이트도 함께 만든다.
- **취합:** `consolidate.py`가 여러 탭을 공통 키로 모은다. 결과는 INDEX/MATCH 수식으로 연결된 통합관리 시트이며, 원본 탭은 모두 보존한다. `recalc.py`가 Excel 또는 LibreOffice로 다시 계산한다.

마지막으로 `verify_excel.py`가 결과를 검사한다. 원본 변경, 기록 없는 셀 변경, 후보 값 수정, 원본 탭 누락, 수식 오류, 근거 없는 인사이트 숫자를 잡아낸다.

## 데모

| 이렇게 요청하면 | 이런 결과가 나온다 |
|-----------------|--------------------|
| "실습1_고객관리_원본.xlsx 정리해줘. 중복 지우고 전화번호·가입일 형식 맞춰줘" | 33행 → 31행, 전화 24·날짜 24건 통일, 확인 필요 6건(전화 오류 2, 이메일 오타 2, 모호한 날짜 1, 극단값 1), 유사 중복 1쌍 |
| "실습2 매출 데이터 분석해서 월별 추이랑 카테고리 비교 차트, 인사이트 정리해줘" | 분석 시트 6개, 엑셀 차트 5개, 숫자 근거가 붙은 인사이트 5개(합계 88,097,750원, 최고 2025-01 등) |
| "실습3 채널 탭들 상품코드 기준으로 취합해줘" | 원본 탭 7개 보존 + 통합관리(상품 108개, 채널별 판매량·매출, 합계, 등록 채널 수), 수식 1,404개 오류 0 |
| "정리하고 분석까지 해줘" | 정리 결과 파일을 입력으로 분석까지 순서대로 |

실습 샘플은 `practice-samples` 스킬로 복사해서 쓴다.

| 세트 | 내용 |
|------|------|
| `excel-practice` | 원본 3종 |
| `excel-practice-answer-key` | 강사용 정답표 |
| `excel-practice-results` | v1.6.1 완성 예시 |

## 요구사항

| 항목 | 필수 | 설치 |
|------|:---:|------|
| Python 3.10+ | ✅ | |
| pandas, openpyxl | ✅ | `python -m pip install -r scripts/requirements.txt -c <저장소>/constraints.txt` |
| Microsoft Excel(Windows) 또는 LibreOffice | | 수식 재계산·오류 확인(`recalc.py`). 없으면 사용자가 Excel로 열어 저장하면 값이 채워진다 |

설치는 `doctor` 스킬이나 다음 명령으로 확인한다.

```bash
python scripts/_vendor/doctor.py --skills excel-automation
```

## 지원 환경

| Claude Code Win | Claude Code Mac | Cowork | claude.ai |
|:-:|:-:|:-:|:-:|
| 지원(Excel 있으면 재계산) | 지원(재계산은 LibreOffice 필요) | 지원(재계산 엔진은 환경에 따라 없음) | 지원(업로드 시 `_vendor` 포함 필요) |

## 커스터마이즈 포인트

플러그인 설치 폴더를 고치지 말고 오버라이드 폴더에 파일을 둔다. 규약은 `references/_shared/overrides.md`에 있다.

- 팀 공용: `<작업 폴더>/.claude/claude-skills/excel-automation/`
- 개인 기본값: `~/.claude/claude-skills/excel-automation/`

| 수준 | 대상 | 파일(스킬 폴더 기준 상대 경로) | 형식 | 예시 |
|:---:|------|-------------------------------|------|------|
| L0 | 모호한 날짜 해석 순서 | `settings.yaml` → `date_order` | `mdy` 또는 `dmy` | `date_order: mdy` (미국식 03/04 = 3월 4일) |
| L0 | 극단값 기준 | `settings.yaml` → `outlier_k` | 숫자(사분위 범위 배수) | `outlier_k: 1.5` (더 민감하게) |
| L0 | 유사 중복 키 | `settings.yaml` → `near_key` | 쉼표로 구분한 열 이름 | `near_key: 이름,연락처` |
| L0 | 완전 중복 유지 | `settings.yaml` → `keep_duplicates` | true/false | `keep_duplicates: true` |
| L0 | 취합 시 없는 항목 표시 | `settings.yaml` → `missing_label` | 문자열 | `missing_label: 미등록` |
| L1 | 범주 표기 사전 | `references/category-map.json` | JSON `{열 또는 "*": {변형: 표준}}` | `{"*": {"서울시 강남구": "서울 강남구"}, "등급": {"vip": "VIP"}}` |
| L2 | 회사 데이터 규칙 | `references/house-rules.md` | 마크다운 | 필수 열, 사번·상품코드 형식, 개인정보 열 처리 원칙 |

범주 사전에 적은 값은 사용자가 정한 규칙이라 자동으로 바꾸고 변경내역에 "사용자 사전"으로 기록한다. 사전에 없는 흔들림은 계속 후보로만 보고한다.

다음 보호 규칙은 오버라이드로 바뀌지 않는다.

- 원본 덮어쓰기 금지
- 이상값·후보 값 자동 수정 금지
- 빈 칸 임의 채우기 금지
- 비밀 정보 파일 기록 금지
- 외부 전송 전 확인

## 데이터 흐름

| 데이터 | 외부 전송 경로 |
|--------|----------------|
| 엑셀 내용 | 프로파일·결과 요약이 Claude 대화에 들어간다. 정리·분석·취합·검증 계산은 모두 로컬 |
| 재계산 | 로컬 Excel(COM) 또는 LibreOffice. 외부 전송 없음 |

개인정보(연락처·이메일)가 있는 파일은 정리 결과 요약에 실제 값을 길게 인용하지 않는다. 후보 시트의 행 번호로 안내한다.

## 변경 이력

| 버전 | 변경 |
|------|------|
| 2.0.0-alpha.1 | 결정적 엔진으로 재설계했다. excel_profile·clean_data·analysis_tools·consolidate·recalc·verify_excel을 추가하고, 원본 보존·변경 기록·후보 보고 원칙을 도입했다. 취합은 INDEX/MATCH 수식과 키 합집합으로 바꿨다. 실습 원본 3종과 정답표를 새로 만들고 v1.6.1 결과물은 완성 예시로 옮겼다 |
| 1.6.1 | 책 출간 시점(코드 예시 중심 SKILL.md) |
