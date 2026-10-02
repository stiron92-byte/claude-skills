---
name: narration-video
description: >
  텍스트(에세이/명언/스크립트)를 입력하면 AI 이미지 + TTS 나레이션 + 자막 + BGM을 조합하여
  완성된 롱폼 나레이션 영상(1920x1080, 30fps)을 자동 생성합니다.
  모든 처리는 MCP 서버를 통해 호스트 머신에서 실행되므로 컨테이너 환경에서도 동작합니다.
  최종 영상은 사용자의 바탕화면(~/Desktop/narration_output/)에 저장됩니다.
  사용: /narration-video [텍스트파일경로 또는 주제]
argument-hint: "[텍스트파일경로 또는 주제]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, mcp__gemini-proxy__gemini_generate_image, mcp__gemini-proxy__gemini_generate_tts, mcp__gemini-proxy__gemini_generate_text, mcp__gemini-proxy__gemini_analyze_audio, mcp__gemini-proxy__prepare_text, mcp__gemini-proxy__generate_bgm, mcp__gemini-proxy__compose_video, mcp__gemini-proxy__save_file, mcp__gemini-proxy__read_file
---

# 롱폼 나레이션 영상 자동 생성 스킬

텍스트 입력만으로 완성된 나레이션 영상을 생성합니다.
모든 처리(Gemini API 호출 + FFmpeg 영상합성)는 MCP 서버를 통해 호스트 머신에서 실행됩니다.
최종 영상은 사용자의 바탕화면 `~/Desktop/narration_output/final_video.mp4`에 저장됩니다.

## 실행 절차

### Phase 0: 환경 확인 (필수 선행)

**가장 먼저 MCP gemini-proxy 도구가 사용 가능한지 확인합니다.**

사용 가능한 도구 목록에서 `mcp__gemini-proxy__gemini_generate_text`가 존재하는지 확인합니다.

**MCP 도구가 없는 경우 → 즉시 중단하고 아래 안내를 사용자에게 표시합니다:**

```
⚠️ 이 스킬을 사용하려면 gemini-proxy MCP 서버 설정이 필요합니다.
아래 3단계를 완료한 후 다시 실행해주세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1) uv 설치 (터미널에서 한 줄 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  macOS/Linux:
    curl -LsSf https://astral.sh/uv/install.sh | sh

  Windows:
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 2) Gemini API 키 발급
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  https://aistudio.google.com/app/apikey 에서 "Create API key" 클릭

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 3) Claude Desktop 설정 파일에 MCP 서버 등록
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  설정 파일 위치:
    macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
    Windows: %APPDATA%\Claude\claude_desktop_config.json

  아래 내용을 설정 파일에 추가하세요:
  {
    "mcpServers": {
      "gemini-proxy": {
        "command": "uv",
        "args": ["run", "--directory", "/스킬설치경로/narration-video/mcp_server", "gemini-proxy-mcp"],
        "env": {
          "GEMINI_API_KEY": "발급받은_API_키"
        }
      }
    }
  }

  * "/스킬설치경로/narration-video/mcp_server" 부분을 실제 경로로 변경하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
설정 완료 후 Claude Desktop을 재시작하고 다시 /narration-video 를 실행하세요.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**위 안내를 출력한 후 스킬 실행을 완전히 중단합니다. fallback이나 대체 실행을 절대 하지 않습니다.**

**MCP 도구가 있는 경우 → 아래 Phase들을 순서대로 진행합니다.**

### Phase 1: 텍스트 준비 (MCP)

`prepare_text` MCP 도구를 호출하여 텍스트를 세그먼트로 분할합니다:

- `input_text`: 사용자가 입력한 텍스트 내용
- `input_file`: 또는 텍스트 파일 경로

결과로 `segments_path`(segments.json 위치)와 `output_dir`을 받습니다.
이후 모든 Phase에서 이 경로들을 사용합니다.

### Phase 2: 이미지 생성 (MCP)

1. `read_file` MCP 도구로 `{output_dir}/segments.json`을 읽어 세그먼트를 확인합니다.
2. 사용자에게 이미지 스타일을 질문합니다 (10가지 프리셋):

| # | 키 | 이름 |
|---|-----|------|
| 1 | minimal | 미니멀 일러스트 |
| 2 | watercolor | 수채화 |
| 3 | ghibli | 지브리 / 로파이 애니메이션 |
| 4 | clay3d | 소프트 3D / 클레이 |
| 5 | impressionist | 인상파 유화 |
| 6 | flat | 플랫 디자인 |
| 7 | pencil | 연필 스케치 |
| 8 | cyberpunk | 사이버펑크 네온 |
| 9 | retro | 빈티지 레트로 포스터 |
| 10 | cinematic | 포토리얼리스틱 / 시네마틱 |

3. `gemini_generate_text` MCP 도구로 모든 세그먼트의 시각 프롬프트를 일괄 생성합니다:

```
프롬프트: 아래 나레이션 텍스트 각각을 구체적인 시각 이미지 프롬프트로 변환하세요.
- 추상적 텍스트는 구체적 장면/오브제/메타포로 변환
- 아트 스타일: [선택된 스타일]
- 텍스트/글자는 이미지에 포함하지 않음
- 영어로 2-3문장씩
[세그먼트 텍스트들]
```

4. 각 세그먼트에 대해 `gemini_generate_image` MCP 도구를 호출합니다:
   - prompt: 생성된 시각 프롬프트
   - style: 선택된 스타일 문자열
   - output_path: `{output_dir}/segments/img_001.png` ~ `img_NNN.png`
   - Rate limit 방지를 위해 3초 간격으로 호출

### Phase 3: TTS 나레이션 생성 (MCP)

각 세그먼트에 대해 `gemini_generate_tts` MCP 도구를 호출합니다:
- text: 세그먼트 텍스트
- voice: Kore (기본값)
- output_path: `{output_dir}/segments/tts_001.wav` ~ `tts_NNN.wav`
- Rate limit 방지를 위해 2초 간격으로 호출

응답의 `duration_seconds`를 기록합니다.

### Phase 4: 자막 생성 (MCP)

각 TTS 오디오에 대해 `gemini_analyze_audio` MCP 도구를 호출합니다:
- audio_path: `{output_dir}/segments/tts_NNN.wav`
- prompt: "이 오디오를 듣고 문장별 타임스탬프를 추출하세요. 형식: [MM:SS.ss] 문장내용"

응답에서 타임스탬프를 파싱하여 SRT 자막 파일을 생성합니다.
세그먼트 간 누적 시간과 SEGMENT_GAP(0.5초)을 반영합니다.

SRT 내용을 구성한 후 `save_file` MCP 도구로 호스트에 저장합니다:
- path: `{output_dir}/subtitles.srt`
- content: 생성된 SRT 내용

SRT 형식:
```
1
00:00:00,000 --> 00:04:500
첫 번째 자막 텍스트

2
00:04:500 --> 00:09:000
두 번째 자막 텍스트
```

### Phase 4.5: BGM 자동 생성 (MCP)

`gemini_generate_text` MCP 도구로 텍스트 무드를 분석합니다:

```
프롬프트: 다음 텍스트의 분위기를 분석하여 하나의 무드를 선택하세요.
선택지: calm, inspirational, warm, dramatic, hopeful, meditative
텍스트: [전체 텍스트]
무드 이름만 답하세요.
```

분석된 무드로 `generate_bgm` MCP 도구를 호출합니다:
- segments_json: `{output_dir}/segments.json`
- mood: 분석된 무드
- output_path: `{output_dir}/bgm_auto.m4a`

### Phase 5: 영상 합성 (MCP)

`compose_video` MCP 도구를 호출합니다:
- segments_json: `{output_dir}/segments.json`
- media_dir: `{output_dir}/segments/`
- srt_path: `{output_dir}/subtitles.srt`
- output_path: `{output_dir}/final_video.mp4`
- bgm_path: `{output_dir}/bgm_auto.m4a`

### Phase 5.5: 중간 파일 정리

영상 합성 성공 후, 사용자에게 중간 파일 삭제 여부를 확인합니다.
삭제 대상: `{output_dir}/segments/`, `{output_dir}/subtitles.srt`, `{output_dir}/bgm_auto.m4a`

### Phase 6: 결과 보고

사용자에게 최종 결과를 보고합니다:
- 영상 파일 경로 (호스트 경로이므로 사용자가 직접 열 수 있음)
- 영상 길이, 파일 크기
- "바탕화면의 narration_output 폴더에서 final_video.mp4를 확인하세요!"

## MCP 서버 설정 (필수)

이 스킬이 동작하려면 `gemini-proxy` MCP 서버가 설정되어 있어야 합니다.

### Claude Desktop 설정

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gemini-proxy": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/narration-video/mcp_server", "gemini-proxy-mcp"],
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

### Claude Code 설정

`.mcp.json` (프로젝트 루트):

```json
{
  "mcpServers": {
    "gemini-proxy": {
      "command": "uv",
      "args": ["run", "--directory", "./narration-video/mcp_server", "gemini-proxy-mcp"],
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

## 콘텐츠 유형별 프리셋

| 유형 | 이미지 스타일 | TTS_VOICE | BGM_VOLUME |
|------|---------------|-----------|------------|
| 자기계발 | minimal | Kore | 0.50 |
| 역사 | retro | Charon | 0.12 |
| 요리 | watercolor | Leda | 0.10 |
| 수면/명상 | impressionist | Kore | 0.08 |
| 뉴스 브리핑 | flat | Fenrir | 0.10 |
| 동화/어린이 | ghibli | Aoede | 0.15 |
| SF/미래 | cyberpunk | Fenrir | 0.12 |
| 아트/감성 | pencil | Kore | 0.10 |

## 로컬 직접 실행 (터미널)

MCP 없이 로컬에서 직접 실행할 때는 기존 파이프라인 사용:

```bash
python3 scripts/run_pipeline.py --input "$ARGUMENTS" --config templates/config.yaml --skip-setup
```

## 참고

- 상세 레퍼런스: [reference.md](reference.md)
- 설정 템플릿: [templates/config_template.yaml](templates/config_template.yaml)
- 샘플 입력: [templates/sample_quotes.txt](templates/sample_quotes.txt)
- MCP 서버 소스: [mcp_server/](mcp_server/)
- 설치 가이드: [SETUP.md](SETUP.md)
