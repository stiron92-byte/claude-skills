# Claude Code Skills

책 『Claude Code Skills』에서 다루는 **업무 자동화 스킬 모음**입니다.
8개의 스킬을 **플러그인 하나**로 묶어 배포하므로, 독자는 명령어 두 줄로 전부 설치할 수 있습니다.

## 빠른 시작 (플러그인 설치, 권장)

Claude Code에서 아래 두 줄을 실행하세요.

```
/plugin marketplace add stiron92-byte/claude-skills
/plugin install claude-skills-book
```

설치하면 8개 스킬이 한 번에 등록되고, 별도 명령어 없이 **자연어로 자동 트리거**됩니다.

```
회의록 정리해줘            → meeting-minutes
이 엑셀 분석해줘           → excel-automation
반도체 트렌드 리서치해줘    → data-collector
이 영상으로 쇼츠 만들어줘   → generate-shorts
```

업데이트가 있으면 `/plugin marketplace update claude-skills` 후 다시 설치하면 됩니다.

## 스킬 목록

| 스킬 | 하는 일 | 추가 준비물 |
|------|---------|-------------|
| `doc-automation` | CSV·엑셀·PDF·Word·PPT·HTML·MD 파일로 주간보고 PPT와 요약 이메일 자동 생성 | Python 3.10+ · `scripts/requirements.txt` |
| `excel-automation` | 엑셀 데이터 정리·분석·시각화·멀티탭 취합 | (스크립트 없이 Claude가 코드 생성) |
| `meeting-minutes` | 회의 녹음/텍스트를 회의록으로 자동 정리 (참석자·안건·결정·액션아이템 분류) | 음성 STT 사용 시 `scripts/transcribe.py` 설정 |
| `content-research` | 트렌드·뉴스·콘텐츠 주제 리서치, 콘텐츠 캘린더 | Python 3.10+ · `scripts/requirements.txt` |
| `data-collector` | 관심 분야 데이터 수집 → 분석 → 리서치 보고서 (+ GitHub Actions 자동화 코드 생성) | Python 3.10+ · WebSearch/WebFetch |
| `content-repurpose` | 원본 콘텐츠(대본·강의·블로그)를 플랫폼별 콘텐츠로 변환 | 없음 |
| `generate-shorts` | 롱폼 영상/팟캐스트에서 세로형 쇼츠 10개 자동 생성 | ffmpeg 등 — `scripts/setup.sh`, `reference.md` 참고 |
| `narration-video` | 텍스트 → AI 이미지 + TTS + 자막 + BGM 나레이션 영상 생성 | **uv · Gemini API 키 · MCP 서버** — `skills/narration-video/SETUP.md` 참고 |

> `narration-video`는 로컬 MCP 서버(`gemini-proxy`)와 Gemini API 키가 필요한 가장 무거운 스킬입니다.
> 다른 스킬에 영향을 주지 않도록 자동 활성화하지 않았으니, 사용 시 `SETUP.md`의 3단계를 따라 직접 설정하세요.

## 수동 설치 (개별 스킬만 쓰고 싶을 때)

플러그인 없이 원하는 스킬만 쓰려면 해당 폴더를 개인 스킬 디렉토리에 복사하세요.

```bash
# 예: 회의록 스킬만 설치
cp -r skills/meeting-minutes ~/.claude/skills/meeting-minutes
```

프로젝트 단위로 쓰려면 `~/.claude/skills/` 대신 프로젝트의 `.claude/skills/`에 복사하면 됩니다.

## 요구사항

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+ (스크립트가 있는 스킬 실행 시)
- 스킬별 의존성은 각 스킬의 `scripts/requirements.txt` / `SETUP.md` / `reference.md` 참고

## 저장소 구조

이 저장소는 **두 가지 관점**으로 구성되어 있습니다.

| 경로 | 용도 |
|------|------|
| `chapterN-*/` | **학습용** — 책 챕터별 원본 (원고·예제·실행 결과 포함) |
| `skills/` | **배포용** — 플러그인으로 설치되는 스킬 본체 (위 마켓플레이스가 참조) |
| `.claude-plugin/marketplace.json` | 플러그인 마켓플레이스 매니페스트 |

스킬 내용을 수정할 때는 `skills/<스킬명>/`을 기준으로 변경하세요. (챕터 폴더는 책 본문용 스냅샷입니다.)
