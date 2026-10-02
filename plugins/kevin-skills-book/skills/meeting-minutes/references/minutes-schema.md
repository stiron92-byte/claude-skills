# minutes.json — 구조화 회의록 형식과 작성 규칙

회의록은 바로 문서로 쓰지 않고 minutes.json에 먼저 정리한다. 그래야 `verify_minutes.py`가 녹취와 대조하고,
`build_minutes.py`가 같은 내용을 용도·형식별로 다시 그릴 수 있다.

## 1. 형식

```json
{
  "meta": {
    "title": "마케팅 주간회의(3월 둘째 주)",
    "date": "2026-03-09",            // 녹취·파일에서 확인되면 YYYY-MM-DD, 모르면 "미상"
    "time": "오전 10:00",
    "attendees": ["김민지", "이준호"],  // 녹취에 나온 이름만. 불참자는 absent
    "absent": ["정하늘(휴가)"],
    "role": "PM", "purpose": "team",  // team | report | personal | email
    "language": "ko",                 // en이면 문서 머리말이 영어
    "transcript": "<W>/transcript/transcript.json",
    "corrections": [                  // STT 오인식을 고친 경우만
      {"heard": "김 피암", "corrected": "김PM", "evidence": ["T0002"]}
    ]
  },
  "summary": ["핵심 한 줄", "…"],                  // 2~4개
  "agenda": [{"title": "안건", "points": ["논의 요점"], "evidence": ["T0003"]}],
  "decisions": [{"text": "확정된 내용", "evidence": ["T0008"]}],
  "action_items": [{"task": "할 일", "owner": "이준호", "due": "수요일(3/11)", "evidence": ["T0009"]}],
  "open_questions": [{"text": "결정하지 못한 것", "evidence": ["T0029"]}],
  "sections": [{"title": "리스크 및 이슈", "items": [{"text": "…", "evidence": ["T0006"]}]}],  // 역할별 추가 섹션
  "next_meeting": {"text": "3월 16일 월요일 오전 10시", "evidence": ["T0032"]},  // 없으면 null
  "uncertain": [{"text": "다음 회의 시각이 '52시'로 인식 — 확인 필요", "evidence": ["T0033"]}]
}
```

(`//` 주석은 설명용이다. 실제 파일에는 쓰지 않는다.)

## 2. 무엇이 결정이고 무엇이 아닌가

| 녹취 | 분류 |
|------|------|
| "그럼 30일로 하겠습니다", "확정합니다", "그렇게 진행하죠" | 결정 |
| 앞에서 정했다가 뒤에서 바뀐 안("23일 안은 취소") | 최종안만 결정. 바뀐 사실은 결정 문장 괄호나 안건 요점에 |
| "~하는 것도 생각해 볼 만해요", "검토해 보죠" | 결정 아님 → 안건 요점 또는 미결 |
| "다음 회의 안건으로 넘기죠" | 미결(open_questions) |
| 잡담(점심 메뉴 등) | 쓰지 않는다 |

## 3. 할 일 규칙

- 담당자: 녹취에서 그 일을 맡겠다고 한 사람, 또는 맡긴다고 지목된 사람. 아무도 맡지 않았으면 `"미정"`. 이유가 있으면 `"미정(정하늘 복귀 후 결정)"`.
- 기한: 녹취에 나온 말 그대로("수요일", "이번 주 금요일", "내일"). 없으면 `"미정"`. 회의 날짜를 알면 괄호에 날짜를 붙여도 된다(`수요일(3/11)`). 그 날짜가 그 요일인지 verify가 확인한다.
- 회의 중 누가 요청만 하고 수행자가 불분명한 일("Sarah needs the screenshots by Thursday")은 담당자 `"미정(Sarah 요청)"`처럼 쓴다. 추측해서 사람을 넣지 않는다.
- 근거(evidence)는 맡겠다는 말이나 지시가 있는 발언 번호다. 마무리 정리 발언이 있으면 함께 넣는다.

## 4. 숫자·이름·STT 오인식

- 목표·기준 수치(예산 총액, 동시 사용자 수, 목표 전환율)는 관련 결정·할 일 문장 안에 쓴다. 요약을 줄이는 용도(이메일)에서 가장 먼저 빠지는 정보이기 때문이다.
- 숫자·날짜·금액은 녹취에 나온 값만 쓴다. 단위 표기는 바꿔도 된다(2000만 원 = 2,000만 원). 녹취끼리 숫자가 다르면(예: 한 곳은 "월 1,900원", 결정은 "월 19,900원") 결정 쪽을 쓰고, 다른 쪽은 `uncertain`에 적는다.
- 음성 변환(STT)이 이름·용어를 틀리게 적었다고 판단되면 고쳐 쓰되 `meta.corrections`에 들린 말·고친 말·근거를 선언한다. 녹음 README, 참석자 소개, 사용자 맞춤 용어 사전이 판단 근거다.
- 녹음만으로 확정할 수 없는 값(알아들을 수 없는 시각, 단위가 빠진 숫자)은 추측하지 않는다. `uncertain`에 적고, 문서에는 "확인 필요"로 남긴다.

## 5. verify_minutes 검사와 고치는 법

| 검사 | 고치는 법 |
|------|-----------|
| evidence-missing / evidence-unknown | 근거 발언 번호를 넣는다. 녹취(transcript.txt)에서 찾는다 |
| owner-unsupported | 녹취에 나온 이름으로 쓰거나 `미정`. STT 오인식이면 corrections 선언 |
| due-unsupported | 근거 발언에 있는 기한 표현으로 바꾸거나 `미정`. 근거 번호가 틀렸을 수도 있다 |
| due-date-mismatch | 괄호 날짜를 회의일 기준으로 다시 계산하거나 지운다 |
| number-provenance | 녹취에 있는 값으로 바꾼다. 계산한 값(합계·비율)은 쓰지 않거나 녹취 숫자로 풀어 쓴다 |
| attendee-unsupported | 녹취에 없는 사람을 지운다(사용자가 알려 준 참석자는 그 이름이 녹취에 없으면 corrections로) |
| correction-unsupported | heard가 근거 발언에 실제로 있는지 확인한다 |
| rendered-missing / leftover / promo-text | build_minutes.py로 다시 렌더링한다. 문서를 손으로 고쳤다면 빠진 항목을 되살린다 |
| 경고 low-confidence-evidence | STT 확신이 낮은 발언(줄 끝 `(?)`)을 근거로 썼다. 내용이 맞는지 다시 보고 `uncertain`에 적는다 |
| 경고 stt-low-accuracy | 한국어를 base 이하 모델로 변환했다. 전달할 때 정확도 한계와 확인 필요 항목을 알린다 |
