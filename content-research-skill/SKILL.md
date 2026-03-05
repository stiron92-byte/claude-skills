---
name: content-research
description: Use when the user wants content ideas, topic suggestions, trend research, or news collection. 트렌드 찾기, 콘텐츠 리서치, 유튜브 주제 선정, 유튜브 영상 주제 추천, 유튜브 컨텐츠 뭐 만들지, 어떤 컨텐츠가 좋을지, 영상 주제 뽑아줘, 블로그 기획, 블로그 글감, 뉴스레터 발행, 뉴스레터 소재, 뉴스 자동 수집, 뉴스 정리, 관심 분야 뉴스, 트렌드 분석, 요즘 뜨는, 이번 주 트렌드, 콘텐츠 아이디어, 콘텐츠 캘린더, 컨텐츠 추천, 컨텐츠 기획, 요약 브리핑, 식품 트렌드, 시장 브리핑, 핫한 여행지, 주목할 제품, RSS 수집, YouTube topics, content research, trending topics, content calendar, what content to make, blog planning, newsletter.
allowed-tools: Bash(python *) Bash(pip *) Bash(mkdir *) Bash(cp *) Bash(cat *)
argument-hint: "[분야: tech/cooking/finance/travel 등]"
---

# 콘텐츠 리서치 자동화

관심 분야 뉴스·트렌드를 자동 수집 → 콘텐츠 아이디어 + 요약 브리핑 생성.

```
질문 수집 → config 생성 → RSS 수집 → Claude 분석 → 브리핑 출력
```

## ⛔ 절대 규칙

**코드 생성, 파일 생성, 스크립트 실행을 하기 전에 반드시 아래 질문을 모두 완료하라.**
사용자 답변이 모두 확보되기 전까지 어떤 파일도 생성하지 않는다.
사용자가 "알아서 해줘"라고 해도, 최소한 관심 분야와 콘텐츠 용도는 반드시 확인한다.

## Step 1: 질문 (반드시 먼저 실행)

스킬 호출 즉시 아래 질문을 사용자에게 한다. $ARGUMENTS가 있으면 해당 항목은 건너뛴다.

**질문 목록:**

1. **관심 분야** — "어떤 분야의 트렌드를 수집할까요? (예: 테크/AI, 요리, 금융, 여행, 한국IT)"
2. **RSS 피드** — "수집할 RSS 피드 URL이 있으신가요? 없으면 분야에 맞게 추천해드립니다."
3. **콘텐츠 용도** — "콘텐츠 용도가 무엇인가요? (유튜브 주제 선정 / 블로그 기획 / 뉴스레터 / 일반 트렌드 파악)"
4. **출력 언어** — "브리핑을 한국어로 작성할까요, 영어로 작성할까요?"

한 번의 메시지로 모든 질문을 묻는다. 여러 번 나눠서 질문하지 않는다.

**RSS 추천 테이블 (사용자가 RSS를 모를 때 제안):**

| 분야 | 추천 피드 |
|------|----------|
| 테크/AI | `https://hnrss.org/frontpage`, `https://techcrunch.com/feed/`, `https://www.theverge.com/rss/index.xml` |
| 요리 | `https://www.seriouseats.com/feed`, `https://www.bonappetit.com/feed/rss`, `https://www.maangchi.com/feed` |
| 금융 | `https://feeds.bloomberg.com/markets/news.rss` |
| 여행 | Lonely Planet RSS, Nomadic Matt RSS |
| 한국 IT | `https://news.hada.io/rss`, `https://yozm.wishket.com/magazine/feed/` |

## Step 2: config 생성 (답변 확보 후)

모든 답변을 받은 뒤, 프로젝트 디렉토리와 `config.yaml`을 생성한다.

```yaml
# config.yaml 구조
rss_feeds:
  - "사용자 답변 또는 추천 URL"
max_entries_per_feed: 10
filter_days: 3
content_type: "youtube"   # 사용자 답변: youtube / blog / newsletter / general
model: "claude-sonnet-4-20250514"
max_tokens: 4096
language: "ko"            # 사용자 답변: ko / en
analysis_prompt: ""       # 비워두면 content_type 기본 프롬프트 사용
```

실행 순서:
1. 프로젝트 디렉토리 생성 (`mkdir -p content-research/output`)
2. 스킬 디렉토리(`scripts/`)에서 파이썬 스크립트 복사, 없으면 직접 생성
3. `config.yaml` 작성 (사용자 답변 기반)
4. `.env` 작성 (`ANTHROPIC_API_KEY` 입력 안내)
5. 가상환경 생성 + 의존성 설치

```bash
cd content-research
python -m venv .venv
source .venv/bin/activate
pip install feedparser anthropic pyyaml python-dotenv
```

**ANTHROPIC_API_KEY는 절대 직접 입력하지 않는다.** 사용자에게 `.env` 파일을 편집하라고 안내한다.

## Step 3: 파이프라인 실행

```bash
python scripts/main.py               # RSS 수집 + 분석 + 브리핑 출력
python scripts/main.py --calendar    # 3개월 콘텐츠 캘린더 생성
```

실행 결과:
- `output/articles_YYYYMMDD_HHMMSS.json` — 수집된 기사 원본
- `output/briefing_YYYYMMDD_HHMMSS.md` — 분석 브리핑

## 용도별 분석 프롬프트

| content_type | Claude가 생성하는 내용 |
|-------------|---------------------|
| youtube | 영상 제목 5개 + 썸네일 아이디어 + 타겟 시청자 + 관심도 |
| blog | SEO 최적화 제목 + 키워드 3-5개 + 글 구조 |
| newsletter | 인사말 + TOP 3 뉴스 요약 + 심화 분석 1개 + 마무리 |
| general | 트렌드 요약 3-5개 + 콘텐츠 아이디어 5개 + 키워드 + 한줄평 |

## 파일 구조

```
content-research/
├── SKILL.md
├── scripts/
│   ├── rss_collector.py
│   ├── content_analyzer.py
│   ├── main.py
│   ├── setup_wizard.py
│   └── requirements.txt
├── templates/
│   └── config.example.yaml
└── references/
    └── SETUP-GUIDE.md
```
