---
name: hwpx-editor
description: 한글(HWPX) 문서의 양식(기관 로고, 결재란, 표, 서체, 배치)은 그대로 두고 글자만 바꿔 새 .hwpx 파일을 만든다. "이 양식은 그대로 두고 내용만 바꿔줘", "결재문서 담당자·결재자 바꿔줘", "기관명이랑 제목만 바꿔줘", "이 한글 양식에 데이터 채워줘", "{{변수}} 들어간 hwpx 템플릿 채우기", "공문·기안문·결과보고서 양식 재사용"처럼 .hwpx 파일의 내용 교체를 요청할 때 사용한다. 한글 문서를 읽어 PPT·요약을 만드는 일(doc-automation 담당), 구버전 .hwp(바이너리) 파일, 양식 없이 새 한글 문서를 처음부터 만드는 일에는 쓰지 않는다.
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
  book-chapter: "2"
---

# HWPX 양식 보존 편집

관공서·공공기관 문서는 정해진 양식 위에 내용만 바꿔 쓴다. 이 스킬은 양식을 1바이트도 망가뜨리지 않고 글자만 바꾼다.
한글 파일(HWPX)은 ZIP 안에 XML 여러 개가 든 구조이고, 한컴오피스는 XML 구조가 조금만 달라도 파일을 열지 못한다.
그래서 편집은 반드시 이 스킬의 스크립트로 하고, XML 파서로 다시 쓰지 않는다.

## 언제 쓰는가 / 쓰지 않는가

| 상황 | 이 스킬 | 다른 방법 |
|------|:------:|-----------|
| 기존 HWPX 문서의 제목·기관명·담당자·본문 교체 | ✅ | |
| `{{변수}}`가 들어 있는 HWPX 양식 채우기 | ✅ | |
| 한글 문서를 읽어 PPT·요약·이메일 만들기 | | doc-automation |
| `.hwp`(구버전) 파일 | | 한컴오피스에서 "다른 이름으로 저장 → HWPX"로 바꾼 뒤 이 스킬 사용 |
| 양식 없이 새 한글 문서 작성 | | 지원하지 않음. 비슷한 양식 파일을 받아서 진행 |

## 시작 전에

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 적용된 사용자 맞춤(기관 양식·용어집)을 확인하고, 있으면 한 줄로 알린다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill hwpx-editor --skill-dir ${CLAUDE_SKILL_DIR} --list
   ```

2. 결과는 원본과 다른 이름으로 저장한다. 출력 폴더: `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/paths.py hwpx-editor --create`

## 워크플로

```
- [ ] 1. 원문 확인(extract) — 바꿀 글자를 원문 그대로 찾는다
- [ ] 2. 치환 맵 작성 — 원문 조각 단위로, 새 내용은 원래 길이와 비슷하게
- [ ] 3. plan 통과(PLAN OK) — 모든 대상이 문서에 있는지 먼저 확인
- [ ] 4. 치환 실행(replace 또는 fill)
- [ ] 5. 검증 통과(HWPX VERIFY OK)
- [ ] 6. 결과 전달 + 한컴오피스에서 열어 확인하도록 안내
```

### 1. 원문 확인

```bash
python ${CLAUDE_SKILL_DIR}/scripts/hwpx_template.py extract 원본.hwpx              # 텍스트 조각 단위
python ${CLAUDE_SKILL_DIR}/scripts/hwpx_template.py extract 원본.hwpx --paragraphs # 문단 단위
```

- 한 문장이 여러 조각(run)으로 나뉘어 있을 수 있다. 조각 목록과 문단 목록을 비교해 실제 조각 단위로 치환 대상을 정한다.
- `{{변수}}`가 보이면 양식 채우기(fill) 경로다. `scan`으로 변수 목록을 확인한다.

### 2. 치환 맵 작성

`map.json`에 `{"원문": "새 글", ...}`를 쓴다. 원문은 extract 결과를 복사해 띄어쓰기·특수문자까지 똑같이 맞춘다.

- 사용자가 준 값(기관명, 담당자, 결재자 등)은 그대로 쓴다. 사용자가 주지 않은 사실(날짜, 인원, 실적 수치)을 지어내지 않는다. 필요하면 묻거나 `○○` 같은 빈칸 표시로 남기고 알린다.
- 본문을 새로 쓸 때는 원래 문장의 길이와 문체(공문체 "~하였습니다", "~바랍니다")를 따른다. 표 칸·결재란은 원래 글자 수의 ±30% 안에서 쓴다. 칸보다 길면 줄이 넘쳐 양식이 깨져 보인다.
- 같은 원문이 여러 곳에 있으면 모두 바뀐다. 한 곳만 바꿔야 하면 앞뒤 조각까지 포함한 더 긴 원문을 쓴다.

### 3. plan — 실행 전 확인

```bash
python ${CLAUDE_SKILL_DIR}/scripts/hwpx_template.py plan 원본.hwpx --map map.json
```

`PLAN OK`가 나와야 다음 단계로 간다. `PLAN MISSING`이면 출력의 `hints`를 보고 맵을 고친다(조각 분할, 띄어쓰기 차이가 대부분이다).

### 4. 치환 실행

```bash
python ${CLAUDE_SKILL_DIR}/scripts/hwpx_template.py replace 원본.hwpx --map map.json --output <출력폴더>/결과.hwpx
python ${CLAUDE_SKILL_DIR}/scripts/hwpx_template.py fill 양식.hwpx --data data.json --output <출력폴더>/결과.hwpx
```

replace는 찾지 못한 대상이 하나라도 있으면 파일을 만들지 않는다. 새 글자는 자동으로 XML 이스케이프된다(`&`, `<`, `>`).

### 5. 검증

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify_hwpx.py 원본.hwpx <출력폴더>/결과.hwpx --map map.json
```

`HWPX VERIFY OK`가 아니면 전달하지 않는다. 검사 내용: mimetype 위치·무압축, 엔트리 목록 동일, 이미지·설정 파일 바이트 동일, 바뀐 XML의 구조(태그·속성·네임스페이스) 동일, 새 글자 존재·원문 잔존 없음, 남은 `{{변수}}` 없음.

### 6. 전달

- 결과 파일 경로와 바꾼 항목 표(원문 → 새 글)를 보여 준다.
- 한컴오피스에서 열어 줄바꿈·칸 넘침을 눈으로 확인하도록 안내한다. 줄 배치는 한컴오피스가 열 때 다시 계산한다.

## 건너뛰기 쉬운 단계 (합리화 표)

| 이런 생각이 들면 | 실제로는 | 그래서 |
|------------------|----------|--------|
| "XML 파서로 읽고 쓰면 더 깔끔하다" | 네임스페이스 접두사가 ns0 등으로 바뀌어 한컴오피스가 파일을 못 연다 | 스크립트만 쓴다 |
| "plan은 생략하고 바로 replace" | 조각이 나뉜 원문은 조용히 안 바뀐다. strict 모드가 막지만 원인 파악이 늦어진다 | plan부터 |
| "검증은 파일이 만들어졌으니 됐다" | 열리지 않는 파일도 만들어진다 | verify 통과 전 전달 금지 |
| "빈칸은 그럴듯한 값으로 채우자" | 공문서에 지어낸 날짜·수치가 들어간다 | 묻거나 ○○로 남기고 알린다 |
| "원본에 바로 저장하면 편하다" | 양식 원본이 사라진다 | 항상 새 파일 |

## 맞춤(오버라이드)

- 기관 표준 양식: 오버라이드 폴더의 `templates/` 아래에 두면 사용자가 파일을 주지 않았을 때 이 양식을 제안한다.
- 기관 용어집·직위 표기 규칙: `references/glossary.md`
- 기본 기관명 등: `settings.yaml`의 `default_org`, `default_department`
- 규약 전체: `references/_shared/overrides.md`

## 참고

- `references/hwpx-guide.md` — HWPX 구조, 조각 분할, linesegarray, 자주 나는 문제(편집이 안 될 때 읽는다)
- 환경 규약: `references/_shared/environment.md`
