# Claude Code Skills

Claude Code에서 사용할 수 있는 자동화 스킬 모음집입니다.
각 챕터는 독립적으로 사용할 수 있는 하나의 스킬입니다.

## Chapters

| # | 스킬 | 한줄 요약 |
|---|------|----------|
| 1 | [문서·PPT 자동화](./chapter1-doc-automation/) | 주간 보고를 15분에 끝내기 |
| 2 | [콘텐츠 리서치 자동화](./chapter2-content-research/) | 트렌드 찾기를 자동으로 |
| 3 | [콘텐츠 대량 생산](./chapter3-content-repurpose/) | 하나 만들면 열 개가 나오게 |
| 4 | [유튜브 쇼츠 자동 생성](./chapter4-generate-shorts/) | 롱폼 하나로 쇼츠 10개 |
| 5 | [롱폼 나레이션 영상 자동 생성](./chapter5-narration-video/) | 원하는 주제만 넣으면 영상이 나온다 |
| 6 | [데이터 수집 시스템](./chapter6-data-collector/) | 내 분야의 데이터를 자동으로 모으기 |

## Getting Started

각 챕터 디렉토리의 `SKILL.md`를 Claude Code의 `.claude/commands/`에 복사하면 슬래시 명령어로 사용할 수 있습니다.

```bash
# 예시: chapter1 스킬 설치
cp chapter1-doc-automation/SKILL.md ~/.claude/commands/doc-automation.md
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+ (스크립트 실행 시)
- 각 챕터별 추가 요구사항은 해당 디렉토리의 README 또는 SKILL.md 참고
