---
name: doc-automation
description: 여러 형식의 자료(PDF, Word, PPT, 한글 HWPX, 엑셀·CSV, 웹페이지 URL, 텍스트)를 읽고 보고 대상에 맞춘 보고용 PPT와 요약 이메일을 만든다. 모든 숫자는 출처와 대조해 검증하고, 회사 PPT 템플릿이 있으면 그 디자인을 따른다. "이 PDF 분석해서 과장님께 보고할 PPT 만들어줘", "이 자료들로 회사 소개 발표자료 만들어줘", "매출 데이터로 주간 보고 PPT", "이 링크 내용으로 팀장님 보고 5장", "회사 템플릿으로 보고서", "보고 메일까지 써줘"처럼 자료를 바탕으로 보고서·발표 PPT나 보고 이메일을 요청할 때 사용한다. 한글 양식의 내용만 바꾸는 일은 hwpx-editor, 엑셀 파일 자체의 정리·분석·취합은 excel-automation, 자료 없이 처음부터 쓰는 글이나 PPT 디자인 템플릿만 만드는 일에는 쓰지 않는다.
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
  book-chapter: "2"
---

# 문서·PPT 보고 자동화

보고서의 가치는 "누가 무엇을 판단하는 데 쓰는가"에서 나온다. 그래서 이 스킬은 파일을 슬라이드로 옮기지 않는다.
자료를 끝까지 읽고 → 보고 대상이 알고 싶은 결론부터 스토리라인을 설계하고 → 일관된 디자인으로 그린 뒤 →
모든 숫자를 출처와 대조해 검증한다. 지어낸 숫자가 한 개라도 있으면 보고서 전체를 믿을 수 없게 되기 때문이다.

## 언제 쓰는가 / 쓰지 않는가

| 상황 | 이 스킬 | 다른 스킬 |
|------|:------:|-----------|
| 자료(파일·URL)를 근거로 보고·발표 PPT, 보고 이메일 | ✅ | |
| 회사 PPT 템플릿에 맞춘 보고서 | ✅ | |
| 한글(HWPX) 양식은 그대로 두고 글자만 바꾸기 | | hwpx-editor |
| 엑셀 데이터 정리·통계·멀티탭 취합(결과가 엑셀) | | excel-automation |
| 공식 pptx 스킬이 있고, 9종 슬라이드로 표현 못 하는 디자인(인포그래픽·이미지 중심) | 내용 설계까지 | pptx 스킬로 렌더링 후 이 스킬의 검증 실행 |

## 시작 전에

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 적용된 사용자 맞춤을 확인한다. 회사 템플릿·설정이 있으면 "적용된 맞춤: 회사 템플릿(templates/brand.pptx)"처럼 한 줄로 알린다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill doc-automation --skill-dir ${CLAUDE_SKILL_DIR} --list
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill doc-automation --skill-dir ${CLAUDE_SKILL_DIR} --settings
   ```

2. 작업 폴더를 정한다: `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/paths.py doc-automation --create` → 이하 `<W>`
3. 필요한 패키지가 없다는 오류가 나면 `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/doctor.py --skills doc-automation`의 해결 명령을 안내한다.

## 워크플로

```
- [ ] 1. 보고 맥락 정리 — 대상·목적·관심 포인트·분량·산출물
- [ ] 2. 자료 추출 — 출처 ID(S01…)가 붙은 텍스트 묶음
- [ ] 3. 자료 정독 — 모든 S*.md를 끝까지 읽는다
- [ ] 4. 스토리라인(outline.json) — 결론 먼저, 슬라이드당 메시지 하나, 숫자마다 출처
- [ ] 5. 렌더링(build_deck)
- [ ] 6. 품질 게이트 — verify_deck 통과 + 이미지로 눈 검수
- [ ] 7. (요청 시) 보고 이메일
- [ ] 8. 전달 — 파일, 슬라이드 요약, 가정·확인 필요 사항
```

### 1. 보고 맥락 정리

사용자 메시지에서 아래를 뽑는다. 없으면 기본값으로 진행하고, 8단계에서 "이렇게 가정했다"고 알린다. 입력 파일이 없을 때만 먼저 묻는다.

| 항목 | 예 | 기본값 |
|------|-----|--------|
| 보고 대상 | 과장님, 팀장님, 임원, 투자 심사역, 고객 | settings `default_audience` 또는 "팀장" |
| 대상의 관심 포인트 | "환율 방향", "리스크 요인", "매수 타이밍인지" | 자료에서 판단에 필요한 핵심 2~3개 |
| 분량 | "5장 이내" | settings `max_slides` 또는 표지 포함 6~8장 |
| 산출물 | PPT, 이메일, 둘 다 | PPT |
| 템플릿 | 사용자 제공 파일 > 오버라이드 `templates/brand.pptx` > 기본 디자인 | |

사용자가 준 관심 포인트는 그대로 슬라이드 제목이나 섹션이 되어야 한다. 그 포인트에 답하지 않는 보고서는 실패다.

### 2. 자료 추출

```bash
python ${CLAUDE_SKILL_DIR}/scripts/extract_sources.py <파일 또는 폴더 ...> --out <W>/sources
```

- 웹페이지 URL은 WebFetch로 읽어 `<W>/inputs/<이름>.md`로 저장한다. 첫 줄에 URL과 가져온 시각을 적고, 그 파일을 추출 입력에 포함한다. 그래야 웹 숫자도 출처 대조가 된다.
- 결과 표의 `error`·`unsupported` 항목은 숨기지 않고 사용자에게 알린다. 예: 배포용(암호화) HWPX는 읽을 수 없으니 PDF로 저장해 달라고 안내하고, 나머지 자료로 계속한다.
- 표 자료는 앞 30행만 텍스트로 들어간다. 합계·평균은 원본 파일을 pandas로 직접 계산하고, 그 값은 4단계에서 `derived`로 선언한다.

### 3. 자료 정독

`<W>/sources/S*.md`를 모두 끝까지 읽는다. 앞부분만 읽고 쓰면 결론이 뒤에 있는 보고서(전망, 리스크, 결론 장)를 놓친다. 3만 자가 넘는 자료는 목차를 먼저 보고 관련 절을 찾아 읽는다.

### 4. 스토리라인 설계 — outline.json

`references/storyline.md`(보고 유형별 구성·헤드라인 작성법)와 `references/outline-schema.md`(형식)를 읽고 `<W>/outline.json`을 쓴다.

- **결론 먼저**: 표지 다음 장에 대상이 가장 알고 싶은 답(요약 KPI 또는 핵심 메시지)을 둔다.
- **헤드라인은 문장**: "환율 동향"이 아니라 "이번 주 달러/원은 1,450원대 상단 테스트 가능성이 크다". 45자 이내.
- **슬라이드당 메시지 하나**: 상위 항목 6개 이하. 넘치면 슬라이드를 나눈다.
- **숫자 규칙**: 슬라이드의 모든 숫자는 (a) 출처 텍스트에 있거나, (b) `derived`에 계산식과 입력을 적은 계산값이거나, (c) 사용자가 대화에서 준 값(`given`)이어야 한다. 출처에 없는 수치는 쓰지 않는다. 모르면 "자료에 없음"이라고 쓴다.
- **출처**: 내용 슬라이드마다 `sources`에 `"S01 p.3"`처럼 적는다. 슬라이드 하단에 파일명으로 표시된다.
- **투자 판단**: "매수 타이밍인지" 같은 요청에는 데이터가 보여 주는 신호와 리스크를 정리하고 매수·매도를 권하지 않는다. 마지막 장에 "투자 권유가 아닌 참고 자료"라고 적는다.

### 5. 렌더링

```bash
python ${CLAUDE_SKILL_DIR}/scripts/build_deck.py <W>/outline.json --out <W>/<보고서이름>.pptx --sources <W>/sources [--template <회사템플릿.pptx>]
```

출력 끝의 경고(글자 넘침 위험, 헤드라인 길이, 항목 과다)는 outline을 고쳐 다시 빌드한다.
9종(표지·목차·구분·글머리·KPI·차트·표·2단·마무리)으로 표현할 수 없는 디자인이 필요하고 공식 pptx 스킬이 있으면, outline을 설계도로 삼아 pptx 스킬로 그린다. 이 경우에도 6단계 검증은 똑같이 한다.

### 6. 품질 게이트

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify_deck.py <W>/<보고서이름>.pptx --sources <W>/sources --outline <W>/outline.json
python ${CLAUDE_SKILL_DIR}/scripts/render_slides.py <W>/<보고서이름>.pptx --out <W>/preview
```

- `DECK VERIFY OK`가 나올 때까지 고친다. `number-provenance` 오류는 숫자를 출처 값으로 바꾸거나, 계산값이면 `derived`에 계산식을 선언한다. 오류를 피하려고 숫자를 지우거나 뭉뚱그리지 않는다.
- `RENDER OK`면 PNG를 한 장씩 열어 겹침·잘림·빈 공간·읽기 어려운 차트를 확인하고 고친다. `RENDER UNAVAILABLE`이면 8단계에서 사용자에게 열어서 확인해 달라고 요청한다.

### 7. 보고 이메일 (요청 시)

`templates/email/executive.md`(임원·상위 보고) 또는 `templates/email/team.md`(팀 공유) 구조로 쓴다. 템플릿 경로는 `overrides.py --resolve templates/email/executive.md`로 찾는다(회사 양식 우선). 이메일의 숫자도 PPT와 같은 출처 규칙을 따른다. `<W>/email_*.md`로 저장한다.

### 8. 전달

1. 결과 파일 경로(링크)
2. 슬라이드별 헤드라인 목록(장 번호 · 한 줄)
3. 가정한 것(대상, 분량 등)과 읽지 못한 자료, 사용자가 확인할 숫자
4. verify_deck 결과 한 줄(대조한 숫자 수, 미확인 0)

## 빠른 주간보고 모드 (매출 CSV 전용)

사용자가 매출 형식 CSV(날짜·상품·매출·판매량 열)로 "주간보고 바로 만들어줘"처럼 정형 5장 보고서를 원할 때만 쓴다. 그 외에는 위 워크플로를 따른다.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/generate_report.py --input <매출.csv> --output <W> [--template <회사.pptx>]
```

## 건너뛰기 쉬운 단계 (합리화 표)

| 이런 생각이 들면 | 실제로는 | 그래서 |
|------------------|----------|--------|
| "PDF 앞부분만 봐도 요지는 안다" | 전망·리스크·결론은 뒤에 있다 | S*.md 전체 정독 |
| "대략적인 숫자면 충분하다" | 보고서의 숫자 하나가 틀리면 전체 신뢰가 무너진다 | 출처 숫자만, 계산값은 derived 선언 |
| "verify 오류는 숫자를 빼면 사라진다" | 근거 없는 결론만 남는다 | 출처를 찾아 연결하거나 계산식을 선언 |
| "사용자가 급하니 이미지 검수는 생략" | 글자 겹침은 열어 보기 전엔 안 보인다 | render_slides로 확인 |
| "관심 포인트는 내용에 녹여 넣었다" | 대상은 자기 질문의 답을 찾지 못한다 | 포인트를 헤드라인·섹션으로 명시 |
| "매수 타이밍이냐고 물었으니 답을 주자" | 투자 권유는 보호 규칙 위반이다 | 신호·리스크·데이터로 답하고 고지 문구 |

## 맞춤(오버라이드)

회사 템플릿(`templates/brand.pptx`), 기본 보고 대상·분량·글꼴·강조색(`settings.yaml`), 이메일 양식, 회사 보고서 구성 규칙(`references/house-style.md`)을 바꿀 수 있다. 목록은 README의 "커스터마이즈 포인트", 규약은 `references/_shared/overrides.md`.

## 참고

- `references/storyline.md` — 보고 유형별 슬라이드 구성, 대상별 강조점, 헤드라인 작성법(4단계에서 읽는다)
- `references/outline-schema.md` — outline.json 형식과 예시(4단계에서 읽는다)
- `references/design-rules.md` — 차트 선택, 표·KPI 쓰는 법, 피해야 할 디자인(5·6단계에서 문제를 고칠 때)
- 회사 맞춤 규칙이 있으면 `overrides.py --resolve references/house-style.md`로 찾아 먼저 읽는다
- 환경 규약: `references/_shared/environment.md`
