# 콘텐츠 리서치 — 상세 설정 가이드

## 1. 사전 준비

- Python 3.10+
- Anthropic API 키 ([console.anthropic.com](https://console.anthropic.com)에서 발급)

## 2. 수동 설치 (스킬 없이 CLI로 사용)

```bash
mkdir content-research && cd content-research
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt
cp templates/config.example.yaml config.yaml
```

`.env` 파일 생성:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## 3. config.yaml 설정

### RSS 피드

```yaml
rss_feeds:
  - "https://hnrss.org/frontpage"
  - "https://techcrunch.com/feed/"
```

RSS URL을 찾는 방법:
- 사이트 URL 뒤에 `/feed`, `/rss`, `/atom.xml` 시도
- 브라우저에서 페이지 소스 보기 → `application/rss+xml` 검색
- Google에서 `사이트명 RSS feed` 검색

### 콘텐츠 유형

```yaml
# youtube: 영상 제목 + 썸네일 + 타겟 시청자
# blog: SEO 제목 + 키워드 + 글 구조
# newsletter: TOP 3 뉴스 + 심화 분석
# general: 트렌드 + 아이디어 + 키워드
content_type: "youtube"
```

### 커스텀 프롬프트

기본 프롬프트 대신 직접 작성:

```yaml
analysis_prompt: "이 뉴스에서 30대 직장인 타겟 유튜브 주제 5개를 뽑아줘"
```

## 4. 실행

```bash
# 전체 파이프라인 (수집 + 분석)
python scripts/main.py

# 3개월 콘텐츠 캘린더 생성
python scripts/main.py --calendar

# 개별 실행
python scripts/rss_collector.py                          # RSS만 수집
python scripts/content_analyzer.py output/articles_*.json # 분석만
```

## 5. 분야별 커스텀 예시

### 요리 유튜버

```yaml
rss_feeds:
  - "https://www.seriouseats.com/feed"
  - "https://www.bonappetit.com/feed/rss"
  - "https://www.maangchi.com/feed"
content_type: "youtube"
analysis_prompt: "이 뉴스에서 요리 유튜브 영상 주제 5개를 뽑아줘"
```

### 테크 유튜버

```yaml
rss_feeds:
  - "https://techcrunch.com/feed/"
  - "https://www.theverge.com/rss/index.xml"
  - "https://hnrss.org/frontpage"
content_type: "youtube"
```

### 금융 블로거

```yaml
rss_feeds:
  - "https://feeds.bloomberg.com/markets/news.rss"
content_type: "blog"
```

## 6. 트러블슈팅

| 증상 | 해결 |
|------|------|
| `feedparser` 설치 오류 | `pip install --upgrade pip && pip install feedparser` |
| RSS 수집 0개 | URL 확인, 브라우저에서 RSS URL 직접 열어보기 |
| Claude API 오류 | `.env`의 `ANTHROPIC_API_KEY` 확인, 잔액 확인 |
