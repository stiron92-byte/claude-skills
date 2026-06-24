# narration-video 스킬 설치 가이드

이 스킬은 **MCP 서버**를 통해 Gemini API를 호출합니다.
MCP 서버는 호스트 머신(사용자 PC)에서 실행되므로, Claude Desktop 컨테이너의 네트워크 차단과 무관하게 동작합니다.

## 사전 준비 (2가지)

### 1. uv 설치

Python 패키지 실행 도구입니다. 터미널에서 한 줄만 실행하면 됩니다.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

설치 확인:
```bash
uv --version
```

### 2. Gemini API 키 발급

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. **Create API key** 클릭
3. 발급된 키를 복사해둡니다 (예: `AIzaSy...`)

---

## Claude Desktop 설정

### Step 1: 스킬 폴더 위치 확인

narration-video 스킬이 설치된 폴더의 **전체 경로**를 확인합니다.

예시:
- macOS: `/Users/홍길동/claude-skills/narration-video`
- Windows: `C:\Users\홍길동\claude-skills\narration-video`

### Step 2: Claude Desktop 설정 파일 편집

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
파일 탐색기에서 `%APPDATA%\Claude\claude_desktop_config.json` 열기

### Step 3: MCP 서버 등록

설정 파일에 아래 내용을 추가합니다:

```json
{
  "mcpServers": {
    "gemini-proxy": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/Users/홍길동/claude-skills/narration-video/mcp_server",
        "gemini-proxy-mcp"
      ],
      "env": {
        "GEMINI_API_KEY": "여기에_발급받은_API_키_입력"
      }
    }
  }
}
```

> **중요:** `/Users/홍길동/claude-skills/narration-video/mcp_server` 부분을
> 실제 narration-video 폴더 안의 `mcp_server` 경로로 변경하세요.

### Step 4: Claude Desktop 재시작

설정 저장 후 Claude Desktop을 완전히 종료했다가 다시 실행합니다.

### Step 5: 동작 확인

Claude Desktop에서 다음과 같이 입력합니다:

```
/narration-video 인생에서 가장 중요한 것은 시간이다
```

정상 동작 시:
- Phase 1: 텍스트 세그먼트 분할
- Phase 2: Gemini로 이미지 생성 (MCP 도구 호출)
- Phase 3: Gemini TTS로 나레이션 생성 (MCP 도구 호출)
- Phase 4: 자막 생성
- Phase 4.5: BGM 생성
- Phase 5: 영상 합성
- 결과: `output/final_video.mp4`

---

## Claude Code (CLI) 설정

### 프로젝트 레벨 설정

프로젝트 루트에 `.mcp.json` 파일을 생성합니다:

```json
{
  "mcpServers": {
    "gemini-proxy": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "./narration-video/mcp_server",
        "gemini-proxy-mcp"
      ],
      "env": {
        "GEMINI_API_KEY": "여기에_발급받은_API_키_입력"
      }
    }
  }
}
```

### 또는 글로벌 설정

`~/.claude/settings.json`에 동일한 `mcpServers` 블록을 추가합니다.

---

## 문제 해결

### "MCP gemini-proxy 도구가 이 환경에 없어"

- **원인**: MCP 서버가 설정되지 않았거나, Claude Desktop을 재시작하지 않음
- **해결**:
  1. 설정 파일 경로 확인 (`claude_desktop_config.json`)
  2. `--directory` 경로가 실제 `mcp_server` 폴더를 가리키는지 확인
  3. Claude Desktop 완전 재시작

### "uv: command not found"

- **원인**: uv가 설치되지 않았거나 PATH에 없음
- **해결**: 위의 uv 설치 명령 실행 후, 터미널/Claude Desktop 재시작

### "GEMINI_API_KEY 환경변수가 설정되지 않았습니다"

- **원인**: 설정 파일의 `env.GEMINI_API_KEY` 값이 비어있음
- **해결**: 실제 API 키로 교체

### "edge-tts가 네트워크 차단으로 실패"

- **원인**: MCP 없이 컨테이너 내부에서 직접 API 호출 시도
- **해결**: 위의 MCP 서버 설정을 완료하면 해결됨 (MCP는 호스트에서 실행되므로 네트워크 차단 없음)

### 설정 경로 빠른 참조

| 환경 | 설정 파일 위치 |
|------|---------------|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Code (프로젝트) | `.mcp.json` (프로젝트 루트) |
| Claude Code (글로벌) | `~/.claude/settings.json` |

---

## 작동 원리

```
사용자 (Claude Desktop/Code)
  │
  ├─ Phase 1: 텍스트 분할 (로컬 Python)
  │
  ├─ Phase 2~4: Gemini API 호출
  │    └─ MCP Tool 호출 → gemini-proxy MCP 서버 (호스트) → Gemini API
  │
  ├─ Phase 4.5: BGM 생성 (로컬 FFmpeg)
  │
  └─ Phase 5: 영상 합성 (로컬 FFmpeg)
       └─ 결과: output/final_video.mp4
```

MCP 서버가 호스트 머신에서 실행되기 때문에 Docker 컨테이너의 네트워크 차단을 우회합니다.
