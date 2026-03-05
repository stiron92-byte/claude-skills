---
name: generate-shorts
description: >
  롱폼 영상/팟캐스트에서 쇼츠 10개를 자동 생성합니다.
  YouTube 자체 자막 추출, 규칙 기반 하이라이트 선별,
  세로 영상(1080x1920) 크롭+자막+인트로/아웃트로 편집까지 한번에 처리합니다.
  유튜브 쇼츠, 인스타 릴스, 틱톡용.
  claude.ai 컨테이너와 로컬 환경 모두 지원합니다.
  사용: /generate-shorts [유튜브URL]
argument-hint: "[youtube-url] [shorts-count]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# YouTube Shorts 자동 생성 스킬

롱폼 영상 하나에서 쇼츠 최대 10개를 자동으로 생성합니다.

## 한줄 실행

```bash
python3 scripts/run_pipeline.py --url "$ARGUMENTS" --count 10 --lang ko
```

이 명령 하나로 Phase 0~4가 순차 실행됩니다.

## 핵심 제약사항

- **디스크 절약 최우선**: torch, openai-whisper 등 대용량 패키지 설치 금지
- **의존성**: ffmpeg + yt-dlp만 사용 (외부 API 없음)
- **자막**: YouTube 자체 제공 자막 (수동 우선, 없으면 자동생성)
- **봇 감지 우회**: 컨테이너 환경 자동 감지, 쿠키/UA/딜레이 조건부 적용
- **한글 지원**: 폰트 자동 탐색 + 설치, 자막/인트로 한글 렌더링

## 환경변수 (모두 선택사항)

- `YT_COOKIE_BROWSER`: 쿠키 브라우저 (기본: chrome, 컨테이너에서는 자동 비활성)
- `YT_PROXY`: 프록시 URL (예: socks5://127.0.0.1:1080)
- `CLAUDE_CONTAINER`: 컨테이너 환경 강제 (1로 설정)

## 실행 절차 (자동)

run_pipeline.py가 아래 Phase를 순차 실행합니다.

### Phase 0: 환경 설정

```bash
bash scripts/setup.sh
```

- ffmpeg, yt-dlp 설치 확인 (sudo 없이 먼저 시도, 실패 시 sudo)
- 한글 폰트(Noto Sans CJK) 설치 (Linux)
- 컨테이너 환경 감지
- output/, output/shorts/, output/logs/ 생성

### Phase 1: 자막 추출

```bash
python3 scripts/extract_subtitles.py --url "$URL" --output output/ --lang ko
```

1. 수동자막 시도 -> 자동자막 시도 -> 아무 언어 시도
2. 브라우저 쿠키: 로컬에서만 사용, 컨테이너는 cookies.txt 폴백
3. 봇 감지 시 지수 백오프 재시도 (3회)
4. 출력: `transcript.json`, `transcript.srt`, `transcript_timestamped.txt`
5. 에러 시 `output/logs/`에 상세 로그

### Phase 2: 하이라이트 자동 선별

```bash
python3 scripts/select_highlights.py --transcript output/transcript.json --output output/highlights.json --count 10 --lang ko
```

**이 Phase는 스크립트가 자동으로 처리합니다 (Claude 개입 불필요).**

선별 로직:
- 슬라이딩 윈도우로 15~60초 구간 후보 생성
- 감정 키워드 사전 기반 스코어링 (한국어/영어)
- 정보 밀도 계산 (음절 수 / 시간)
- 독립성 판단 (맥락 의존 표현 감점: "이것", "아까" 등)
- 겹치지 않는 상위 N개 선별 (greedy)
- 출력: `output/highlights.json`

### Phase 3: 쇼츠 영상 편집

```bash
python3 scripts/generate_shorts.py --highlights output/highlights.json --url "$URL" --output output/shorts/
```

1. 하이라이트 구간만 개별 다운로드 (전체 영상 다운로드 X)
2. 봇 우회 (쿠키 조건부 + UA + 딜레이)
3. 파일명 불일치 시 glob 탐색으로 보정
4. FFmpeg 세로(1080x1920) 크롭 + 한글 폰트 자막
5. 텍스트 인트로(2초) + 아웃트로(2초) - fps 맞춤, concat filter 사용
6. 처리 완료 후 원본 삭제 (tmpdir 자동 정리)
7. 실패 건은 건너뛰고 계속 진행, 실패 사유는 metadata.json + logs에 기록

**출력:**
- `output/shorts/short_01.mp4` ~ `short_10.mp4`
- `output/shorts/metadata.json` (성공/실패 목록, 제목, 해시태그)
- `output/logs/error_*.log` (실패 건 상세 로그)

### Phase 4: 결과 보고

run_pipeline.py가 자동으로 결과를 출력합니다:
- 생성된 쇼츠 수, 실패 수
- 각 쇼츠의 제목과 길이
- 전체 소요 시간
- metadata.json의 제목/설명/해시태그를 업로드에 바로 사용 가능

## 개별 Phase 건너뛰기

이미 실행한 Phase가 있으면 건너뛸 수 있습니다:

```bash
# 환경 설정 건너뛰기
python3 scripts/run_pipeline.py --url "$URL" --skip-setup

# 자막이 이미 추출된 경우
python3 scripts/run_pipeline.py --url "$URL" --skip-setup --skip-subtitles

# 하이라이트가 이미 선별된 경우
python3 scripts/run_pipeline.py --url "$URL" --skip-setup --skip-subtitles --skip-highlights
```

## 참고

- 상세 레퍼런스: [reference.md](reference.md)
- 설정 템플릿: [templates/config_template.yaml](templates/config_template.yaml)
