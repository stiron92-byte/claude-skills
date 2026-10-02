---
name: meeting-minutes
description: 회의 녹음(mp3·wav·m4a 등)이나 회의 텍스트(클로바노트·노션·Zoom·Teams 녹취, SRT·VTT, 붙여 넣은 대화)를 읽어 결정 사항, 할 일(담당자·기한), 미결 사항, 다음 회의를 정리한 회의록을 만든다. 음성은 로컬에서 변환해 외부로 보내지 않고, 모든 결정·할 일에 근거 발언 번호를 붙여 녹취와 대조 검증한다. 팀 공유·상위 보고·개인 기록·이메일 용도와 마크다운·워드·노션·채팅 형식을 지원한다. "이 녹음 회의록으로 정리해줘", "회의록 만들어줘", "미팅 노트 정리", "녹취록에서 할 일만 뽑아줘", "회의 내용 팀장님께 보고용으로", "meeting minutes", "인터뷰·상담 녹음 정리"처럼 회의·인터뷰 기록을 정리하는 요청에 사용한다. 회의 내용으로 발표 PPT를 만드는 일은 doc-automation(회의록을 자료로 넘김), 회의 일정 잡기·초대 메일 발송, 녹음 없이 회의 안건을 새로 쓰는 일에는 쓰지 않는다.
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
  book-chapter: "4"
---

# 회의록 정리

회의록이 틀리는 지점은 대개 세 곳이다. 아무도 맡지 않은 일에 담당자를 지어 넣고, 회의 중에 번복된 안을 결정으로 적고, 음성 변환(STT)이 잘못 들은 이름·숫자를 그대로 옮긴다.
그래서 이 스킬은 녹취에 발언 번호(T0001…)를 붙이고, 회의록의 결정·할 일마다 근거 번호를 달아 `verify_minutes.py`로 대조한 뒤에 문서를 만든다.

## 언제 쓰는가 / 쓰지 않는가

| 상황 | 이 스킬 | 다른 스킬 |
|------|:------:|-----------|
| 회의·인터뷰·상담 녹음 또는 녹취 텍스트 → 회의록 | ✅ | |
| 녹취에서 할 일·결정만 뽑기 | ✅ | |
| 회의 내용으로 보고 PPT | 회의록까지 | doc-automation(회의록 파일을 자료로) |
| 회사 워드 양식에 맞춘 회의록 | 내용 정리·검증 | 공식 docx 스킬이 있으면 그 스킬로 서식 |
| 일정 잡기, 초대·회의록 메일 발송 | | 메일·캘린더 도구(보내기 전 사용자 확인) |

## 시작 전에

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 사용자 맞춤을 확인한다. 기본 역할·용도·형식, STT 모델, 용어 사전이 있으면 "적용된 맞춤: 기본 용도 팀 공유, 용어 사전"처럼 한 줄로 알린다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill meeting-minutes --skill-dir ${CLAUDE_SKILL_DIR} --list
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill meeting-minutes --skill-dir ${CLAUDE_SKILL_DIR} --settings
   ```

2. 작업 폴더를 정한다: `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/paths.py meeting-minutes --create` → 이하 `<W>`
3. 음성 변환에 필요한 패키지가 없다는 오류가 나면 `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/doctor.py --skills meeting-minutes`의 해결 명령을 안내한다. 텍스트 입력은 추가 설치가 필요 없다.

## 워크플로

```
- [ ] 1. 용도 정하기 — 역할·용도·형식(요청 → 맞춤 기본값 → 팀 공유·마크다운), 필요할 때만 한 번 확인
- [ ] 2. 번호 붙은 녹취 만들기 — 음성: transcribe / 텍스트: prepare_transcript
- [ ] 3. 녹취 정독 — 끝까지 읽고, (?) 발언과 STT 오인식 후보를 표시
- [ ] 4. minutes.json 작성 — 결정·할 일·미결에 근거 번호, 모르는 담당자·기한은 "미정"
- [ ] 5. 검증 — verify_minutes 통과
- [ ] 6. 렌더링 — build_minutes, 렌더링 결과까지 verify
- [ ] 7. 전달 — 파일, 결정·할 일 요약, 미정·확인 필요 항목
```

### 1. 용도 정하기

| 항목 | 정하는 순서 | 기본값 |
|------|-------------|--------|
| 역할 | 요청("PM으로서", "영업팀 공유") → settings `default_role` | 일반(역할별 섹션 없음) |
| 용도 | 요청("팀장님 보고", "메일로 보낼") → settings `default_purpose` | team(팀 공유) |
| 형식 | 요청("워드로", "노션에 붙일") → settings `default_format` | md(마크다운 파일) |

요청이나 맞춤 기본값으로 정해지면 묻지 않는다. 셋 다 정해지지 않았고 사용자에게 물을 수 있으면, 기본값을 제시하며 한 번에 묻는다("팀 공유용 마크다운으로 만들까요? 보고용·워드가 필요하면 알려 주세요"). 물을 수 없으면 기본값으로 만들고 7단계에서 알린다.

### 2. 번호 붙은 녹취 만들기

음성 파일:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/transcribe.py <녹음 파일> --out-dir <W>/transcript --language ko [--glossary <용어.md>]
```

- 시작할 때 출력되는 파일 길이·모델·예상 시간을 사용자에게 알린다. 모델 선택, 용어 사전, 긴 녹음 이어하기는 `references/stt.md`.
- 참석자 이름을 알고 있으면(녹음 README, 사용자 메시지) 용어 사전 파일로 만들어 `--glossary`로 넘긴다. 기본은 교정 참고용이다. 인식 힌트(`--hotwords`)는 이름 오인식을 줄이지만 숫자를 망가뜨릴 수 있어 숫자가 중요한 회의에는 쓰지 않는다.

텍스트(파일 또는 붙여 넣은 대화):

```bash
python ${CLAUDE_SKILL_DIR}/scripts/prepare_transcript.py <녹취 파일 또는 <W>/input.txt> --out-dir <W>/transcript
```

붙여 넣은 텍스트는 먼저 `<W>/input.txt`로 저장한다. 클로바노트·SRT·VTT·워드·화자 표기를 자동 감지한다.

### 3. 녹취 정독

`<W>/transcript/transcript.txt`를 끝까지 읽는다. 결정은 회의 끝 "정리하겠습니다" 부분에서 번복되는 경우가 많다.
줄 끝 `(?)` 발언, 문맥에 맞지 않는 이름·숫자(예: 같은 가격이 한 곳은 1,900원, 결정은 19,900원)를 표시해 둔다.

### 4. minutes.json 작성

`references/minutes-schema.md`(형식·결정 판별·할 일 규칙)를 읽고 `<W>/minutes.json`을 쓴다. 역할별 추가 섹션은 `references/output-templates.md`.

- 결정은 확정된 최종안만. 번복된 안, "검토해 보죠" 같은 의견은 결정이 아니다.
- 할 일 담당자·기한은 녹취에 있는 그대로. 없으면 `"미정"`. 사람을 추측해 넣지 않는다.
- 목표·기준 수치(예산, 동시 사용자 10,000명, 전환율)는 관련 결정·할 일 문장에 함께 쓴다. 이메일처럼 짧은 용도에서도 빠뜨리지 않는다.
- STT 오인식을 고쳐 쓰면 `meta.corrections`에 선언한다. 확정할 수 없는 값은 `uncertain`에 적는다.

### 5. 검증

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify_minutes.py <W>/minutes.json --transcript <W>/transcript/transcript.json
```

`MINUTES VERIFY OK`가 나올 때까지 minutes.json을 고친다. 오류를 피하려고 결정·할 일을 지우지 않는다. 검사별 고치는 법은 `references/minutes-schema.md` §5.

### 6. 렌더링

```bash
python ${CLAUDE_SKILL_DIR}/scripts/build_minutes.py <W>/minutes.json --out <W>/<회의명>_회의록.md --purpose team --format md
python ${CLAUDE_SKILL_DIR}/scripts/verify_minutes.py <W>/minutes.json --transcript <W>/transcript/transcript.json --rendered <W>/<회의명>_회의록.md
```

- 형식: `md`, `docx`, `notion`, `text`(채팅·메일 본문). 채팅 출력을 원하면 `text`로 만들어 그 내용을 답변에 붙인다.
- md·docx는 끝에 근거 발언 대조표가 붙는다(검토·감사용). 빼려면 `--evidence none`.
- 공식 docx 스킬이 있고 회사 워드 양식이 필요하면, minutes.json을 내용으로 삼아 그 스킬로 문서를 만들고 같은 `--rendered` 검증을 한다.

### 7. 전달

1. 결과 파일 경로(링크)
2. 결정 n개, 할 일 n개(담당자 미정 n개, 기한 미정 n개) — 미정 항목은 누가 정해야 하는지와 함께
3. 확인 필요 항목(`uncertain`, STT 오인식 교정 내용). 한국어를 base 모델로 변환했다면 그 사실
4. 가정한 것(용도·형식 기본값), verify 결과 한 줄

결과물과 답변에 스킬 소개·홍보 문구를 넣지 않는다. 이어서 할 수 있는 일은 요청과 관련된 것만 한 줄로 제안한다(예: "이 회의록으로 보고 PPT가 필요하면 doc-automation으로 이어 만들 수 있다").

## 건너뛰기 쉬운 단계 (합리화 표)

| 이런 생각이 들면 | 실제로는 | 그래서 |
|------------------|----------|--------|
| "역할·용도·형식을 꼭 먼저 물어야 한다" | 요청에 이미 답이 있거나 기본값이면 충분한 경우가 대부분 | 정해지지 않았을 때만 기본값과 함께 한 번 |
| "담당자가 없으니 말한 사람을 넣자" | 아무도 맡지 않은 일이 회의록에서 누군가의 일이 된다 | "미정"과 정할 사람·시점 |
| "처음 정한 날짜도 결정이다" | 번복된 안이 실행된다 | 최종안만 결정, 번복은 괄호로 |
| "STT가 '김 피암'이라 썼으니 그대로" | 참석자 이름이 틀린 회의록은 신뢰를 잃는다 | 근거와 함께 corrections 선언 |
| "숫자가 좀 이상해도 녹취에 있으니 쓰자" | STT가 자릿수를 빠뜨린 것일 수 있다 | 다른 발언과 대조, 어긋나면 uncertain |
| "근거 번호는 번거롭다" | 검증할 수 없는 회의록은 다시 들어야 한다 | 결정·할 일마다 번호 |
| "완료 후 스킬 활용법을 알려 주자" | 결과물에 섞인 홍보 문구는 노이즈다 | 넣지 않는다 |

## 맞춤(오버라이드)

기본 역할·용도·형식과 STT 모델(`settings.yaml`), 참석자·용어 사전(`references/glossary.md`), 회의 유형별 구성 규칙(`references/meeting-types.md`)을 바꿀 수 있다.
목록은 README의 "커스터마이즈 포인트", 규약은 `references/_shared/overrides.md`.

## 참고

- `references/minutes-schema.md` — minutes.json 형식, 결정·할 일·숫자 규칙, verify 검사별 고치는 법(4·5단계)
- `references/output-templates.md` — 용도별 구성, 역할별 추가 섹션(4·6단계)
- `references/stt.md` — 모델 선택, 용어 사전, 긴 녹음, 텍스트 대안, 알려진 문제(2단계)
- 회사 회의 유형 규칙이 있으면 `overrides.py --resolve references/meeting-types.md`로 찾아 먼저 읽는다
- 환경 규약: `references/_shared/environment.md`
