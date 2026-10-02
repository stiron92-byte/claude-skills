---
name: excel-automation
description: 엑셀·CSV 파일을 정리(중복 제거, 전화번호·날짜 형식 통일, 오타·이상값·빈 칸 보고), 분석(요약 통계, 월별 추이, 항목별 비교, 엑셀 차트, 숫자 근거가 붙은 인사이트), 멀티탭 취합(공통 키로 여러 탭을 수식 연결된 통합 관리 시트로)한다. 원본은 바꾸지 않고 새 파일에 저장하며 모든 변경을 기록하고 검증한다. "이 고객 명단 정리해줘", "중복 지우고 전화번호 형식 맞춰줘", "매출 엑셀 분석해서 차트랑 인사이트", "카테고리별 매출 비교", "채널 탭들 상품코드로 취합해줘", "시트 합쳐서 관리표 만들어줘"처럼 엑셀 데이터를 가공·분석·병합하는 요청에 사용한다. 엑셀 숫자로 보고용 PPT나 메일을 만드는 일은 doc-automation, 웹·API에서 데이터를 모으는 일은 data-collector, 셀 몇 개 수정이나 서식만 다듬는 단순 편집에는 쓰지 않는다.
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
  book-chapter: "3"
---

# 엑셀 정리·분석·취합 자동화

엑셀 작업의 실패는 대부분 조용히 일어난다. 중복으로 지운 행이 사실 다른 사람이었거나, 이상해 보이는 값을 "고쳐서" 원래 정보가 사라지거나,
취합 시트에 값을 붙여 넣어 원본을 고쳐도 반영되지 않는 식이다. 그래서 이 스킬은 규칙이 정해진 일은 검증된 스크립트로 하고,
사람이 판단할 값은 고치지 않고 보여 주며, 결과를 전달하기 전에 `verify_excel.py`로 원본·결과·기록을 대조한다.

## 언제 쓰는가 / 쓰지 않는가

| 상황 | 이 스킬 | 다른 스킬 |
|------|:------:|-----------|
| 명단·주문 데이터의 중복·형식·오타·빈 칸 정리 | ✅ 기능 1 | |
| 매출·실적 데이터의 통계·추이·비교·차트·인사이트 | ✅ 기능 2 | |
| 여러 탭(채널·지점·월)을 공통 키로 한 시트에 모으기 | ✅ 기능 3 | |
| 분석 결과로 보고용 PPT·보고 메일 | 분석까지 | doc-automation |
| 웹·API에서 데이터 수집 | | data-collector |
| 셀 몇 개 수정, 서식·인쇄 설정만 변경 | | 직접 편집(공식 xlsx 스킬이 있으면 그 스킬) |

공식 xlsx 스킬이 설치되어 있으면 복잡한 서식(재무 모델 색 규칙, 인쇄 영역, 양식 디자인)은 그 스킬의 방법을 따른다.
이 경우에도 원본 보존·변경 기록·`verify_excel.py` 검증은 이 스킬 규칙대로 한다.

## 시작 전에

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 적용된 사용자 맞춤을 확인한다. 있으면 "적용된 맞춤: settings.yaml(outlier_k), 범주 사전"처럼 한 줄로 알린다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill excel-automation --skill-dir ${CLAUDE_SKILL_DIR} --list
   ```

2. 작업 폴더를 정한다: `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/paths.py excel-automation --create` → 이하 `<W>`
3. 패키지가 없다는 오류가 나면 `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/doctor.py --skills excel-automation`의 해결 명령을 안내한다.
4. 회사 데이터 규칙이 있으면 `overrides.py --resolve references/house-rules.md`로 찾아 먼저 읽는다(필수 열, 코드 형식, 금지 처리).

## 워크플로

```
- [ ] 1. 구조 파악(excel_profile) — 시트·머리글·열 의미·키 후보·중복 수
- [ ] 2. 기능 판단 — 정리 / 분석 / 취합 (복합이면 정리 → 분석 순서)
- [ ] 3. 실행 — 정리: clean_data / 분석: analysis_tools / 취합: consolidate
- [ ] 4. 재계산(수식이 있으면 recalc)
- [ ] 5. 품질 게이트 — verify_excel 통과
- [ ] 6. 전달 — 파일, 숫자로 된 변경 요약, 확인 필요 항목
```

### 1. 구조 파악

```bash
python ${CLAUDE_SKILL_DIR}/scripts/excel_profile.py <파일.xlsx>
```

시트별 머리글 행(제목 행이 위에 있어도 찾음), 열 의미(phone·email·date·number·code·text), 키 후보, 일련번호 열, 완전 중복 수, 수식·병합 셀 수, 시트 간 공통 열, 추천 기능을 보여 준다.
열 추정이 틀렸으면 3단계에서 열을 직접 지정한다. 추정에 맞춰 데이터를 바꾸지 않는다.

### 2. 기능 판단

| 요청 | 기능 |
|------|------|
| 정리·클리닝·중복·형식 통일·오류 찾기 | 1 정리 |
| 분석·통계·추이·비교·차트·인사이트 | 2 분석 |
| 취합·합치기·통합·탭 병합·관리표 | 3 취합 |

요청이 애매하면 프로파일의 추천 기능과 근거(예: "탭 7개에 상품코드 공통 열")를 보여 주고 확인한다. "정리하고 분석까지"면 정리 결과 파일을 분석 입력으로 쓴다.

### 3-1. 기능 1: 정리

```bash
python ${CLAUDE_SKILL_DIR}/scripts/clean_data.py <원본.xlsx> --out <W>/<이름>_정리.xlsx --near-key 이름,연락처
```

- 완전 중복(일련번호 열 제외 모든 값 같음)만 지운다. 이름·연락처 같은 핵심 열만 같은 **유사 중복은 지우지 않고** `유사중복_후보` 시트로 보여 준다. 어느 행이 맞는지는 사람이 정한다.
- 전화번호·날짜는 안전하게 바꿀 수 있는 값만 통일한다. 자릿수 오류, 영문 O 혼입, 월·일이 모호한 날짜(03/04/2024), 두 자리 연도는 원래 값 그대로 두고 후보로 보고한다.
- 이메일 도메인 오타, 극단값, 범주 표기 흔들림은 고치지 않고 `오타_이상값_후보` 시트에 제안과 함께 적는다. 빈 칸은 채우지 않고 `빈칸현황`에 적는다.
- 사용자가 "모호한 날짜는 미국식이야"처럼 규칙을 주면 `--date-order mdy`로 다시 실행한다. 규칙 없이 추측하지 않는다.
- 엔진이 다루지 않는 정리(주소 분리, 이름 성·이름 분리 등)는 `references/cleaning.md`의 기록 방식을 따라 pandas로 하고 변경내역에 같은 형식으로 남긴다.

### 3-2. 기능 2: 분석

거래 데이터(날짜·금액 열)의 기본 분석은 표준 보고서로 시작한다.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify_excel.py snapshot <원본.xlsx> --out <W>/snapshot.json
python ${CLAUDE_SKILL_DIR}/scripts/analysis_tools.py report <원본.xlsx> --out <W>/<이름>_분석.xlsx --date-col 주문일 --value-col 결제금액 --category-col 카테고리 --item-col 상품명
```

원본 시트를 보존하고 요약통계·월별추이(전월 대비)·카테고리별(비중)·월x카테고리(히트맵 서식)·상위항목 시트와 엑셀 차트, 인사이트 시트를 만든다.
사용자의 질문("지난달 대비 변화", "지역별 객단가")이 표준 보고서에 없으면 `references/analysis.md`의 도구(`write_df`, `add_chart`, `write_insights`)로 시트를 더한다.

- 차트는 엑셀 기본 차트로 만든다. 그림(PNG) 차트는 값을 확인할 수 없다.
- 인사이트는 3~5개, 각 문장의 숫자는 통합 문서의 셀 값이어야 하고 근거 셀을 함께 적는다. 계산한 비율·증감은 먼저 시트에 쓰고 그 값을 인용한다.
- 원인을 데이터 없이 단정하지 않는다("2월 매출 감소는 설 연휴 영향" ✗ → "2월이 최저, 원인 확인 필요" ✓).

### 3-3. 기능 3: 취합

`references/consolidation.md`를 읽고 spec.json(키 열, 탭별로 가져올 열과 새 이름, 합계·등록 수 열)을 쓴다. 키 열과 탭 구조는 1단계 프로파일의 공통 열·키 후보로 정한다.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/consolidate.py <원본.xlsx> --spec <W>/spec.json --out <W>/<이름>_통합.xlsx
```

- 원본 탭은 모두 그대로 두고 맨 앞에 `통합관리`·`취합리포트` 시트를 더한다.
- 통합 키는 모든 탭 키의 합집합이다. 일부 탭에만 있는 항목도 빠지지 않고, 없는 탭 칸은 빈 칸(또는 settings `missing_label`)이다.
- 값은 `IFERROR(INDEX(...,MATCH(...)),"")` 수식으로 원본 탭을 참조한다. 원본 탭을 고치면 통합 시트가 따라온다. XLOOKUP·FILTER·UNIQUE는 쓰지 않는다(Excel 2019 이하·LibreOffice에서 깨짐).

### 4. 재계산

수식을 쓴 결과는 `consolidate.py`가 끝에서 자동으로 재계산한다. 직접 수식을 넣었다면 실행한다.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/recalc.py <W>/<결과.xlsx>
```

`RECALC OK ... errors=0`이어야 한다. 오류 셀이 나오면 수식을 고친다. `RECALC UNAVAILABLE`(Excel·LibreOffice 없음)이면 6단계에서 "파일을 Excel로 열어 저장하면 값이 채워진다"고 알린다.

### 5. 품질 게이트

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify_excel.py clean <원본.xlsx> <W>/<이름>_정리.xlsx
python ${CLAUDE_SKILL_DIR}/scripts/verify_excel.py analysis <원본.xlsx> <W>/<이름>_분석.xlsx --snapshot <W>/snapshot.json
python ${CLAUDE_SKILL_DIR}/scripts/verify_excel.py consolidate <원본.xlsx> <W>/<이름>_통합.xlsx
```

`VERIFY OK`가 나올 때까지 고친다. 오류를 피하려고 검사 대상(인사이트 숫자, 변경 기록, 원본 탭)을 지우지 않는다. 검사 이름과 고치는 법은 `references/cleaning.md`·`references/analysis.md`·`references/consolidation.md` 끝의 표에 있다.
엔진 없이 정리했거나 직접 수식을 짰다면 같은 검사를 통과하도록 report.json 형식(`references/cleaning.md`)을 맞추거나, consolidate 모드에 `--sheet`·`--key`를 준다.

### 6. 전달

1. 결과 파일 경로(링크). 원본은 바뀌지 않았다는 확인(verify의 input 해시 대조)
2. 숫자로 된 요약: 정리 "33행 → 31행, 중복 2건 삭제, 전화 24·날짜 24건 통일, 확인 필요 6건" / 분석 "인사이트 5개, 차트 5개" / 취합 "상품 108개, 원본 탭 7개 보존, 수식 1,404개 오류 0"
3. 사람이 결정할 것: 후보 시트의 항목(전화번호 오류, 이메일 오타, 모호한 날짜, 극단값, 유사 중복)
4. 가정한 것(열 추정, 키 열, 날짜 순서)과 verify 결과 한 줄

## 건너뛰기 쉬운 단계 (합리화 표)

| 이런 생각이 들면 | 실제로는 | 그래서 |
|------------------|----------|--------|
| "이 정도 정리는 pandas로 바로 하면 된다" | 매번 다른 코드는 매번 다른 실수를 한다(번호 열 때문에 중복을 못 찾는 등) | clean_data 엔진 사용, 빠진 기능만 직접 |
| "이름·연락처가 같으니 중복이다" | 등급·주소가 다르면 갱신된 정보일 수 있다 | 유사 중복은 후보로 보고 |
| "98,000,000원은 0이 하나 더 붙은 오타다" | 실제 대량 구매일 수 있다 | 고치지 않고 후보로 |
| "03/04/2024는 3월 4일이겠지" | 4월 3일일 수도 있다 | 원래 값 유지, 사용자 규칙을 받으면 --date-order |
| "값으로 붙여 넣는 게 깔끔하다" | 원본 탭을 고쳐도 통합 시트가 따라오지 않는다 | INDEX/MATCH 수식 |
| "재계산은 사용자가 열면 된다" | 열기 전에는 #N/A 오류를 아무도 모른다 | recalc로 계산하고 오류 0 확인 |
| "인사이트 숫자는 대충 맞다" | 표와 다른 숫자 하나가 분석 전체의 신뢰를 깬다 | 셀 값만 인용, verify로 대조 |
| "원본에 바로 저장하면 편하다" | 되돌릴 수 없다 | 항상 새 파일, verify가 원본 해시 확인 |

## 맞춤(오버라이드)

날짜 순서·극단값 기준·유사 중복 키(`settings.yaml`), 범주 표기 사전(`references/category-map.json`), 취합 시 없는 항목 표시, 회사 데이터 규칙(`references/house-rules.md`)을 바꿀 수 있다.
목록은 README의 "커스터마이즈 포인트", 규약은 `references/_shared/overrides.md`. 원본 덮어쓰기 금지와 이상값 자동 수정 금지는 맞춤으로 바뀌지 않는다.

## 참고

- `references/cleaning.md` — 정리 규칙의 근거, report.json·변경내역 형식, 엔진 밖 정리를 기록하는 법, verify 검사 표(3-1·5단계)
- `references/analysis.md` — 질문별 분석·차트 선택, 도구 함수 사용법, 인사이트 작성 규칙(3-2단계)
- `references/consolidation.md` — spec.json 형식, 키 열 고르기, 레이아웃, 수식 규칙(3-3단계)
- 환경 규약: `references/_shared/environment.md`
