# generate-shorts 레퍼런스

## 파이프라인 구조 (큐레이션 모드 — 기본)

```
run_pipeline.py --candidates-only
  |-> setup.sh                              (Phase 0: 환경 설정)
  |-> extract_subtitles.py                  (Phase 1: 자막 추출)
  |-> select_highlights.py --mode candidates (Phase 2a: 후보 ~25개)
[Claude: candidates.json 검토 -> highlights.json 작성]   (Phase 2b)
generate_shorts.py --highlights ...          (Phase 3: 쇼츠 생성)
[Claude: 프레임 추출 -> 검수 체크리스트]      (Phase 3.5)
```

전자동 모드는 `run_pipeline.py --url URL` (Phase 2b/3.5 생략, 품질 낮음).

## 카드뉴스 모드 (card_news.py)

- 디자인 상수는 스크립트 상단에 고정: 1080x1920, 네이비 그라데이션(#12182E→#080910),
  옐로 액센트(#FFC400), 민트 라벨(#94E2D5), 포인트 박스(#1C223A)
- 텍스트 넘침 방지: `fit_font`(폭 초과 시 폰트 자동 축소), `wrap_body`(측정 기반 줄바꿈+말줄임)
- 카드 영상 조립: 카드당 N초 + xfade 크로스페이드(offset = i*(N-fade)) + zoompan 미세 줌
  (2배 업스케일 후 줌 — 저해상도 zoompan의 떨림 완화). `--bgm` 없으면 무음 트랙(anullsrc) 삽입
- 의존성: Pillow(렌더), ffmpeg(영상). 외부 API 불필요

## 후크 오버레이

검은 인트로 카드(기본 꺼짐) 대신, 본편 첫 2.5초 위에 후크 텍스트를 얹는다:

```
drawtext=textfile='hook.txt':fontsize=64:fontcolor=white:
  x=(w-text_w)/2:y=h*0.14:line_spacing=14:
  box=1:boxcolor=black@0.45:boxborderw=22:
  enable='between(t,0,2.5)':fontfile='...'
```

- 텍스트는 textfile로 전달 (따옴표/콜론 이스케이프 문제 회피, 여러 줄 지원)
- `wrap_text()`가 12자 기준으로 자동 줄바꿈
- 관련 config: `hook_overlay`, `hook_duration`, `hook_font_size`, `intro_card`, `outro_enabled`

## 봇 감지 우회 전략

### 환경별 동작

| 환경 | 쿠키 | User-Agent | 딜레이 | 프록시 |
|------|------|-----------|--------|--------|
| 로컬 (macOS/Linux) | --cookies-from-browser chrome | OS별 Chrome UA | 2~5초 랜덤 | YT_PROXY |
| 컨테이너 (claude.ai) | cookies.txt 폴백 | Linux Chrome UA | 2~5초 랜덤 | YT_PROXY |

### 컨테이너 감지 조건

다음 중 하나라도 해당하면 컨테이너로 판단:
- `/home/claude` 디렉토리 존재
- `CLAUDE_CONTAINER=1` 환경변수
- `/.dockerenv` 파일 존재

### 실패 시 체크리스트

1. yt-dlp 최신 버전: `yt-dlp -U`
2. 쿠키 파일 배치: `cookies.txt`를 작업 디렉토리에
3. 프록시: `export YT_PROXY=socks5://127.0.0.1:1080`
4. 에러 로그 확인: `output/logs/`

## 한글 폰트

### 자동 탐색 순서

1. `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
2. `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc`
3. `/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc`
4. `/usr/share/fonts/truetype/nanum/NanumGothic.ttf`
5. `/System/Library/Fonts/AppleSDGothicNeo.ttc` (macOS)
6. `fc-list :lang=ko` 결과

### 설치

```bash
# Ubuntu/Debian
apt-get install -y fonts-noto-cjk

# macOS (내장)
```

## 하이라이트 선별 알고리즘

### 스코어링 기준

| 기준 | 최대 점수 | 방법 |
|------|----------|------|
| 감정 강도 | 40 | 감정 키워드 사전 매칭 (한국어 30개+, 영어 15개+) |
| 정보 밀도 | 30 | 음절 수 / 시간 (한국어), 단어 수 / 시간 (영어) |
| 독립성 | 20 | 맥락 의존 표현 감점 ("이것", "아까" 등 -3점씩) |
| 길이 보너스 | 10 | 20~45초 최적, 15~60초 보통 |

### 선별 과정

1. 자막 chunk를 슬라이딩 윈도우로 15~60초 구간 생성
2. 각 윈도우 스코어링
3. 점수 내림차순 정렬
4. Greedy 방식으로 겹치지 않는 상위 N개 선별 (최소 10초 간격)
5. 시간순 정렬 후 출력

## yt-dlp 주요 명령

### 자막 추출

```bash
yt-dlp --write-sub --sub-lang ko --skip-download --convert-subs srt -o "output/manual_sub" URL
yt-dlp --write-auto-sub --sub-lang ko --skip-download --convert-subs srt -o "output/auto_sub" URL
```

### 구간 다운로드

```bash
yt-dlp --download-sections "*125.3-183.7" \
  -f "bestvideo[height<=1080]+bestaudio/best" \
  --merge-output-format mp4 \
  --force-keyframes-at-cuts \
  -o "output.mp4" URL
```

## FFmpeg 주요 명령

### 세로 변환 (레이아웃 3종)

원본 16:9를 9:16으로 바꾸는 방식. 콘텐츠 종류에 맞게 고른다
(자세한 선택 기준은 SKILL.md의 "영상 레이아웃 선택" 표 참고).
아래 필터는 `generate_shorts.py`의 `build_layout_filtergraph()`가 만드는 것과 동일하다.

**fit_blur (기본, 잘림 없음)** — 화면 녹화·코드·슬라이드·강의·게임 등:

```bash
ffmpeg -i input.mp4 -filter_complex \
"[0:v]split=2[bg][fg];\
[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:1[bgb];\
[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fgs];\
[bgb][fgs]overlay=(W-w)/2:(H-h)/2,ass='sub.ass'[outv]" \
  -map "[outv]" -map "0:a?" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k output.mp4
```

> 자막은 `subtitles=`(SRT) 대신 **직접 만든 ASS**(`ass=`)로 굽는다.
> SRT를 subtitles 필터로 쓰면 libass가 PlayRes를 기본 384x288로 잡아 FontSize를
> 최종 프레임(1920)에 6배 이상 확대해 자막이 화면을 덮어버린다.
> `generate_shorts.py`의 `write_ass_from_srt()`가 PlayResX/Y를 1080x1920으로 박은
> ASS를 생성하므로 FontSize가 실제 픽셀이 되고, `WrapStyle: 0`으로 긴 줄이 자동 줄바꿈된다.

**crop (가운데만, 좌우 잘림)** — 인물 중앙 토킹헤드 전용:

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass='sub.ass'" \
  -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k output.mp4
```

**fit (단색 레터박스)**:

```bash
ffmpeg -i input.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,ass='sub.ass'" \
  -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k output.mp4
```

### 텍스트 오버레이 (한글 폰트 지정)

```bash
ffmpeg -y \
  -f lavfi -i "color=c=black:s=1080x1920:d=2:r=30" \
  -f lavfi -i "anullsrc=r=44100:cl=stereo" -t 2 \
  -vf "drawtext=text='제목':fontfile='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc':fontsize=52:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -c:a aac -shortest intro.mp4
```

### concat filter (코덱 불일치 방지)

```bash
ffmpeg -y -i intro.mp4 -i main.mp4 -i outro.mp4 \
  -filter_complex "[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]concat=n=3:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k \
  -movflags +faststart output.mp4
```

## 에러 로깅

모든 subprocess 실패는 `output/logs/error_*.log`에 기록됩니다:
- 실행된 명령어
- returncode
- stdout, stderr 전문

## 디스크 사용량

| 단계 | 예상 용량 (1시간 영상) |
|------|------------------------|
| 자막 추출 | ~0.1MB |
| 구간 다운로드 (1개, tmpdir) | ~15MB |
| 크롭+자막 (1개, tmpdir) | ~8MB |
| 최종 쇼츠 (10개) | ~80MB |
| 피크 사용량 | ~95MB |
