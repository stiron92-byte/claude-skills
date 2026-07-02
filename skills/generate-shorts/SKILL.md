---
name: generate-shorts
description: >
  롱폼 영상/팟캐스트에서 유튜브 쇼츠(인스타 릴스/틱톡)를 자동 생성합니다.
  YouTube 자막 추출 → 후보 구간 스코어링 → Claude가 하이라이트 선별·제목/후크 작성·자막 재구성 →
  세로 영상(1080x1920) 변환 + 후크 오버레이 + 자막 합성 → Claude 프레임 검수.
  화면 녹화·강의·코드·슬라이드처럼 가로가 넓은 영상도 잘림 없이 변환합니다
  (콘텐츠에 맞는 레이아웃 선택: fit_blur/crop/fit).
  카드뉴스 모드도 지원: "카드뉴스", "개념 카드", "카드로 정리" 요청 시
  영상 내용을 요약한 카드 이미지 세트(+ 카드 쇼츠 영상)를 생성합니다.
  claude.ai 컨테이너와 로컬 환경 모두 지원합니다.
  사용: /generate-shorts [유튜브URL]
argument-hint: "[youtube-url] [shorts-count]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# YouTube Shorts 자동 생성 스킬

롱폼 영상 하나에서 쇼츠 여러 개를 만든다. **스크립트는 도구이고, 판단은 Claude가 한다.**
규칙 스코어러는 감정 키워드 개수를 셀 뿐 내용을 이해하지 못하므로, 후보를 추리는 데까지만 쓴다.
어떤 구간이 "쇼츠가 되는지", 제목·후크·자막을 어떻게 쓸지는 Claude가 내용을 읽고 결정한다.
이 큐레이션 단계(Phase 2b)와 검수 단계(Phase 3.5)가 품질을 좌우하므로 건너뛰지 않는다.

## 전체 흐름

| Phase | 주체 | 내용 |
|-------|------|------|
| 0 | 스크립트 | 환경 설정 (ffmpeg, yt-dlp, 한글 폰트) |
| 1 | 스크립트 | YouTube 자막 추출 → transcript.json/srt/txt |
| 2a | 스크립트 | 후보 구간 ~25개 스코어링 → candidates.json |
| **2b** | **Claude** | 후보 검토 → 선별 + 제목/후크 + 자막 재구성 → highlights.json |
| 3 | 스크립트 | 구간 다운로드 → 세로 변환 + 후크 오버레이 + 자막 합성 |
| **3.5** | **Claude** | 프레임 추출해 눈으로 검수, 문제 시 수정 후 재실행 |
| 4 | 스크립트 | 결과 보고 (metadata.json) |

## 실행 명령 (큐레이션 모드 — 기본)

```bash
# Phase 0~2a: 환경 설정 + 자막 추출 + 후보 생성
python3 scripts/run_pipeline.py --url "$URL" --candidates-only

# Phase 2b: Claude가 output/candidates.json → output/highlights.json 작성 (아래 가이드)

# Phase 3: 쇼츠 생성
python3 scripts/generate_shorts.py \
  --highlights output/highlights.json --url "$URL" \
  --output output/shorts/ --srt output/transcript.srt --layout fit_blur

# Phase 3.5: Claude가 프레임 검수 (아래 체크리스트)
```

## Phase 2b: 하이라이트 큐레이션 (Claude가 직접 수행 — 품질의 핵심)

`output/candidates.json`(후보 목록)과 `output/transcript_timestamped.txt`(전체 타임스탬프 대본)를
읽고 최종 `output/highlights.json`을 작성한다. 요청받은 개수만큼 선별한다 (기본 10개, 시험용이면 2~3개).

**선별 기준** — score(규칙 점수) 순이 아니라 내용을 읽고 아래를 만족하는 구간을 고른다:

1. **독립성**: 앞뒤 맥락 없이 그 구간만 봐도 이해된다
2. **후크**: 첫 1~2문장이 궁금증을 만든다 (질문, 반전, 강한 주장, 구체적 숫자)
3. **완결성**: 구간 안에서 작은 결론/페이오프가 나온다
4. **다양성**: 선택된 쇼츠끼리 주제가 겹치지 않는다

**경계 조정**: 후보의 start/end는 참고값이다. transcript_timestamped.txt에서 해당 구간 전후를 보고
문장이 시작되는 지점에서 시작해 결론 문장이 끝나는 지점에서 끝나도록 초 단위로 조정한다 (15~60초 권장).

**제목/후크 작성**:
- 자동자막의 음성인식 오류를 문맥으로 교정한다 (예: "7발1 2입니다" → 실제 발화를 문맥으로 추정)
- `title`: 내용 요약형, 28자 이내
- `hook`: 본편 위에 크게 얹히는 문구 — **20자 이내로 짧고 강하게**. 낚시가 아니라 호기심 유발

**자막 재구성(`subtitles`)**: 자동자막의 롤링 파편을 문장 단위로 다시 쓴다. 이걸 생략하면
원본 자동자막이 그대로 들어가 중복·오인식이 화면에 노출된다 — **생략하지 말 것**.
- 시간은 **구간 시작 기준 상대 초** (start=0.0이 구간 시작), 마지막 이벤트는 구간 길이를 넘지 않게
- 한 이벤트는 1~2줄 분량, 2~5초, 실제 말 타이밍과 대략 일치하게 (transcript_timestamped.txt 참조)
- 음성인식 오류 교정, 간투사("어", "음") 제거

**highlights.json 스키마**:

```json
[
  {
    "index": 1,
    "start": 1065.1,
    "end": 1096.5,
    "title": "스피커 임베딩이 목소리를 결정한다",
    "hook": "AI가 목소리를 배우는 법",
    "reason": "화자 임베딩 개념이 독립적으로 설명되고 결론까지 이어짐",
    "subtitles": [
      {"start": 0.0, "end": 3.5, "text": "화자 테이블에서 스피커 정보를 가져옵니다"},
      {"start": 3.5, "end": 7.0, "text": "이걸 인풋 임베딩에 넣어주면"}
    ]
  }
]
```

## Phase 3.5: 프레임 검수 (Claude가 직접 수행)

생성된 각 쇼츠에서 프레임을 뽑아 Read 도구로 **직접 눈으로** 확인한다:

```bash
ffmpeg -y -ss 1  -i output/shorts/short_01.mp4 -frames:v 1 output/check_01_hook.png   # 후크 구간
ffmpeg -y -ss 10 -i output/shorts/short_01.mp4 -frames:v 1 output/check_01_mid.png    # 본편 중간
```

체크리스트:
- [ ] 화면이 좌우/상하로 잘리지 않았다 (코드·슬라이드 글자가 온전히 보임)
- [ ] 자막이 하단에 적정 크기로 표시되고 화면 밖으로 넘치지 않는다
- [ ] 후크 텍스트가 읽히고, 핵심 콘텐츠를 가리지 않는다
- [ ] 검은 화면/빈 프레임이 없다

문제 발견 시 원인별로 조치한 뒤 **해당 쇼츠만** 재실행한다:
- 자막이 길거나 겹침 → highlights.json의 subtitles를 더 짧게 재작성
- 후크가 콘텐츠를 가림 → hook 문구 단축 또는 config의 hook_duration 축소
- 화면 잘림 → `--layout fit_blur` 확인 (crop은 토킹헤드 전용)

## 영상 레이아웃 선택 (중요)

원본이 16:9 가로 영상일 때 세로(9:16)로 바꾸는 방식. **원본 콘텐츠를 보고 고른다.**

| layout | 동작 | 언제 쓰나 |
|--------|------|-----------|
| `fit_blur` (기본) | 원본 전체를 폭에 맞춰 넣고 위·아래를 블러 배경으로 채움. **아무것도 잘리지 않음** | 화면 녹화, 코드, 슬라이드/강의, 발표, 게임, 표·차트 등 가장자리 정보가 중요한 모든 경우 |
| `crop` | 가운데를 꽉 채우고 좌우를 잘라냄 | 인물이 화면 **중앙**에 있는 토킹헤드·인터뷰·브이로그 전용 |
| `fit` | 단색(검정) 레터박스 | 배경을 깔끔하게 두고 싶을 때 |

**확신이 없으면 `fit_blur`.** 강의·코드·화면 녹화를 `crop`으로 처리하면 좌우가 잘려 못 읽게 된다.

## 전자동 모드 (빠르지만 품질 타협)

Claude 큐레이션 없이 규칙 스코어만으로 한 번에 생성한다. 제목·자막이 자동자막 그대로라
인식 오류와 어색한 구간 선택이 남는다. 데모/시험용으로만 권장.

```bash
python3 scripts/run_pipeline.py --url "$URL" --count 10 --lang ko --layout fit_blur
```

## 카드뉴스 모드 (이미지 세트 + 카드 쇼츠 영상)

"카드뉴스", "개념 카드", "카드로 정리" 같은 요청이면 클립 대신 **내용 요약 카드**를 만든다.
디자인 시스템(다크 네이비 + 옐로 액센트, 1080x1920)은 `scripts/card_news.py`에 고정되어 있고,
Claude는 **내용(cards.json)만** 작성한다. 외부 API 불필요 (Pillow + ffmpeg).

**절차**:

```bash
# 1) 자막 추출 (이미 있으면 생략)
python3 scripts/run_pipeline.py --url "$URL" --candidates-only --skip-setup

# 2) [Claude] transcript를 읽고 output/cards.json 작성 (아래 스키마)

# 3) 카드 렌더링 (+ 옵션: 카드 쇼츠 영상)
python3 scripts/card_news.py --cards output/cards.json --output output/cards/ \
  --video output/cards/cards_short.mp4 --seconds 4

# 4) [Claude] 생성된 PNG를 Read로 열어 검수 (텍스트 넘침/겹침/오탈자)
```

**cards.json 스키마와 작성 규칙**:

```json
{
  "series_label": "Qwen-TTS 파인튜닝 · 핵심 개념",
  "footer": "전체 강의는 채널에서 ▶",
  "cards": [
    {
      "index": 1,
      "title_lines": ["로스는", "낮을수록 좋다?"],
      "punch": "오해입니다",
      "points": [
        {"label": "실전 기준", "body": "여러 번 학습 결과, 로스 12~11 구간이\n가장 안정적인 품질"},
        {"label": "예외 사례", "body": "7까지 내려가도 문제없던 경우 있음"},
        {"label": "진짜 변수", "body": "로스보다 에폭 수가 중요"}
      ]
    }
  ]
}
```

- 카드 1장 = 개념 1개. 보통 3~5장 세트
- `title_lines`: 질문/도발형 문구, **최대 2줄, 줄당 8자 내외** (길면 자동 축소되지만 짧게 쓰는 게 예쁘다)
- `punch`: 반전/답변 한 마디, **8자 이내** (예: "오해입니다", "비밀은 이것")
- `points`: 2~3개. `label` 6자 이내, `body` 2줄 이내(줄당 ~22자, 넘치면 자동 줄바꿈·말줄임)
- 영상 대본의 음성인식 오류는 문맥으로 교정해서 쓴다
- 렌더러가 출력한 "경고"(폰트 축소/잘림)가 있으면 해당 카드 문구를 줄여 다시 렌더링한다

## 핵심 제약사항

- **디스크 절약 최우선**: torch, openai-whisper 등 대용량 패키지 설치 금지
- **의존성**: ffmpeg + yt-dlp만 사용 (외부 API 없음)
- **자막**: YouTube 자체 제공 자막 (수동 우선, 없으면 자동생성)
- **봇 감지 우회**: 컨테이너 환경 자동 감지, 쿠키/UA/딜레이 조건부 적용
- **한글 지원**: 폰트 자동 탐색 + 설치, 자막/후크 한글 렌더링

## 환경변수 (모두 선택사항)

- `YT_COOKIE_BROWSER`: 쿠키 브라우저 (기본: chrome, 컨테이너에서는 자동 비활성)
- `YT_PROXY`: 프록시 URL (예: socks5://127.0.0.1:1080)
- `CLAUDE_CONTAINER`: 컨테이너 환경 강제 (1로 설정)

## 개별 Phase 건너뛰기

이미 실행한 Phase가 있으면 건너뛸 수 있다:

```bash
python3 scripts/run_pipeline.py --url "$URL" --candidates-only --skip-setup                  # 환경 설정 생략
python3 scripts/run_pipeline.py --url "$URL" --candidates-only --skip-setup --skip-subtitles # 자막도 이미 있음
```

## 참고

- 상세 레퍼런스: [reference.md](reference.md)
- 설정 템플릿: [templates/config_template.yaml](templates/config_template.yaml)
