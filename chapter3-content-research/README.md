# content-research

관심 분야 뉴스·트렌드 자동 수집 → 콘텐츠 아이디어 + 요약 브리핑을 생성하는 Claude Code 스킬입니다.

## 주요 기능

- **대화형 설정**: 스킬 호출 시 Claude가 먼저 질문하여 config 자동 생성
- **RSS 자동 수집**: feedparser로 다수 피드에서 뉴스 수집
- **콘텐츠 분석**: Claude API로 트렌드 요약, 아이디어 생성, 키워드 분석
- **용도별 최적화**: 유튜브 / 블로그 / 뉴스레터에 맞는 출력

## 설치

```bash
# 개인 스킬 (모든 프로젝트에서 사용)
cp -r content-research-skill ~/.claude/skills/content-research

# 또는 프로젝트 스킬 (현재 프로젝트에서만)
mkdir -p .claude/skills
cp -r content-research-skill .claude/skills/content-research
```

## 사용

Claude Code에서 `/content-research` 또는 자연어로 호출:

```
유튜브 주제 선정을 위한 뉴스 수집해줘
테크 분야 트렌드 브리핑 만들어줘
콘텐츠 리서치 해줘
```

호출하면 Claude가 **먼저 4가지를 질문**한 뒤 설정을 생성하고 실행합니다:

1. 관심 분야
2. RSS 피드 URL (모르면 추천)
3. 콘텐츠 용도 (유튜브/블로그/뉴스레터/일반)
4. 출력 언어

## 파일 구조

```
content-research/
├── SKILL.md                 ← 스킬 정의
├── scripts/
│   ├── main.py              ← 메인 파이프라인
│   ├── rss_collector.py     ← RSS 수집
│   ├── content_analyzer.py  ← Claude API 분석
│   ├── setup_wizard.py      ← 대화형 설정 마법사
│   └── requirements.txt
├── templates/
│   └── config.example.yaml
└── references/
    └── SETUP-GUIDE.md       ← 상세 가이드
```

## 필수 요구사항

- Python 3.10+
- Anthropic API 키

상세 설정 방법은 `references/SETUP-GUIDE.md` 참조.
