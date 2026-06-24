# 나레이션 영상 생성 - 상세 레퍼런스

## 아키텍처

```
텍스트 입력
    │
    ▼
[Phase 1] 텍스트 분할 → segments.json
    │
    ├──▶ [Phase 2] Gemini 이미지 생성 → img_001.png ...
    │
    ├──▶ [Phase 3] Gemini TTS 생성 → tts_001.wav ...
    │
    ▼
[Phase 4] 타임스탬프 추출 → subtitles.srt
    │
    ▼
[Phase 5] FFmpeg 영상 합성 → final_video.mp4
```

Phase 2와 3은 독립적이므로 병렬 실행 가능합니다.

## API 상세

### Gemini 이미지 생성

- **모델**: `gemini-2.5-flash-image` (안정, 무료 티어 넉넉)
- **폴백**: `gemini-2.0-flash-exp` (이미지 생성 지원 시)
- **해상도**: 1024x1024 (기본), 생성 후 FFmpeg에서 1920x1080으로 리사이즈
- **설정**: `response_modalities=["IMAGE"]`
- **비용**: 이미지당 약 $0.039 (1K 해상도)
- **제한**: 분당 10회 (무료 티어), Rate limit 시 지수 백오프

### Gemini TTS

- **모델**: `gemini-2.5-flash-preview-tts`
- **출력**: PCM 16-bit, 24kHz, mono → WAV 변환
- **보이스 30종**: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat
- **추천 보이스**:
  - 차분한 나레이션: Aoede, Kore
  - 극적 나레이션: Charon, Fenrir
  - 속삭이는 톤: Kore (프롬프트에 "whisper softly" 추가)
  - 앵커 스타일: Fenrir, Orus
  - 따뜻하고 친근: Aoede, Leda

### Gemini 오디오 이해 (타임스탬프)

- **모델**: `gemini-2.5-flash` (오디오 이해 지원)
- **방식**: File API 업로드 → 프롬프트로 타임스탬프 요청
- **토큰**: 초당 32토큰
- **지원 포맷**: WAV, MP3, FLAC, OGG, AAC

## FFmpeg 영상 합성 상세

### 기본 합성 파이프라인

각 세그먼트별:
1. 이미지 → 오디오 길이만큼 정지 영상 (30fps)
2. 자막 오버레이 (ASS 포맷)
3. 세그먼트 간 crossfade 전환 (1초)
4. BGM 믹싱 (볼륨 15%)
5. 최종 출력: H.264, AAC, MP4

### 자막 스타일

```
FontName=Noto Sans CJK KR
FontSize=24
PrimaryColour=&H00FFFFFF
OutlineColour=&H00000000
Outline=2
Shadow=1
MarginV=50
Alignment=2
```

### 해상도 및 크롭

- 출력: 1920x1080 (16:9)
- 이미지 리사이즈: `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2`

## config.yaml 필드 설명

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| IMAGE_STYLE | string | "minimal illustration, soft pastel colors, clean white background" | 이미지 생성 프롬프트 접미사 |
| IMAGE_MODEL | string | "gemini-2.5-flash-image" | Gemini 이미지 모델 |
| TTS_VOICE | string | "Aoede" | TTS 보이스 이름 |
| TTS_MODEL | string | "gemini-2.5-flash-preview-tts" | TTS 모델 |
| TTS_STYLE | string | "" | 나레이션 스타일 (예: "Read calmly and slowly") |
| AUDIO_MODEL | string | "gemini-2.5-flash" | 오디오 이해 모델 |
| BGM_VOLUME | float | 0.15 | BGM 볼륨 (0.0 ~ 1.0) |
| FADE_DURATION | float | 1.0 | 세그먼트 전환 페이드 (초) |
| RESOLUTION | string | "1920x1080" | 출력 해상도 |
| FPS | int | 30 | 출력 프레임레이트 |
| FONT_SIZE | int | 24 | 자막 폰트 크기 |
| SEGMENT_MAX_CHARS | int | 200 | 세그먼트 최대 글자수 |
| LANGUAGE | string | "ko" | 언어 코드 |

## 비용 추정 (명언 12개 기준)

| 항목 | 호출 수 | 단가 | 소계 |
|------|---------|------|------|
| 이미지 생성 | 12회 | ~$0.039 | ~$0.47 |
| TTS 생성 | 12회 | ~$0.01 | ~$0.12 |
| 오디오 분석 | 12회 | ~$0.005 | ~$0.06 |
| **총합** | | | **~$0.65** |

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `GEMINI_API_KEY not set` | 환경변수 미설정 | `.env` 파일에 키 추가 또는 `export GEMINI_API_KEY=...` |
| `ffmpeg: command not found` | FFmpeg 미설치 | `bash scripts/setup.sh` 재실행 |
| 이미지 생성 실패 | Rate limit | config.yaml에서 `IMAGE_DELAY` 값 증가 (기본 3초) |
| TTS 무음 출력 | 빈 텍스트 세그먼트 | segments.json에서 빈 항목 확인 |
| 한글 자막 깨짐 | 폰트 미설치 | `setup.sh`가 자동 설치, 수동: Noto Sans CJK KR |
| 영상 길이 불일치 | 오디오/이미지 동기화 문제 | `--force-duration` 옵션으로 강제 동기화 |
