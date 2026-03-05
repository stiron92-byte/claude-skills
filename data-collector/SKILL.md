---
name: data-collector
description: >
  관심 분야의 데이터를 자동 수집 → 분석 → 트렌드 리서치 보고서 생성.
  "~트렌드 알려줘", "~시장 분석해줘", "~뭐가 뜨고 있어?", "~리서치해줘",
  "데이터 수집해줘", "시장 조사", "경쟁사 분석", "투자 리서치", "트렌드 분석",
  "요즘 뭐가 핫해?", "~분야 어때?", "~시장 현황", "~동향 파악",
  화장품 트렌드, 주식 분석, IT 트렌드, 식품 트렌드, 부동산 시장, 게임 트렌드,
  beauty trend, market research, competitor analysis, investment research,
  데이터 자동 수집, 자동 분석, 리서치 보고서, 시장 브리핑, 산업 분석.
  content-research 스킬과 다른 점: 이 스킬은 "데이터 기반 분석 보고서"를 생성하며,
  과거 동향 → 현재 트렌드 → 미래 예측 구조의 심층 리서치를 제공한다.
  자동화 요청 시 GitHub Actions + 수집 파이프라인 코드도 생성 가능.
allowed-tools: Bash(python *) Bash(pip *) Bash(mkdir *) Bash(cp *) Bash(cat *) Bash(curl *) WebSearch WebFetch
argument-hint: "[키워드 또는 분야: 화장품/반도체/AI/부동산/인디게임 등]"
---

# 데이터 수집 → 분석 → 트렌드 리서치 보고서

관심 분야의 데이터를 자동 수집하고, 분석하여 **과거 → 현재 → 미래 예측** 구조의 트렌드 리서치 보고서를 생성한다.

```
사용자 확인 → Domain 감지 → 데이터 수집 → 분석 → .md 보고서 생성 → viewer 제공
```

---

## 아키텍처: 컨테이너 환경 대응

이 스킬은 컨테이너 기반 Desktop 환경에서 실행된다.
**컨테이너 내부에서는 외부 네트워크 접근이 제한**될 수 있으므로, 모드별로 수집 전략이 다르다.

### 모드 1: 즉시 실행 (기본) — Claude 내장 도구 사용
- **데이터 수집**: Claude의 `web_search`, `WebFetch` 도구를 직접 사용하여 수집한다.
- **Python 스크립트의 `requests`/`feedparser` 등 HTTP 라이브러리를 절대 사용하지 않는다.**
- 수집된 데이터를 JSON 파일로 저장한 뒤, Python `analyzer.py`로 분석하고, `report_generator.py`로 보고서를 생성한다.
- Python은 **로컬 파일 처리(분석, 보고서 생성)에만** 사용한다.

```
[Claude web_search / WebFetch] → 데이터 수집 (Claude가 네트워크 접근)
        ↓ JSON으로 저장
[Python analyzer.py]           → 분석 (로컬 파일 처리, 네트워크 불필요)
        ↓
[Python report_generator.py]   → .md 보고서 생성 (로컬 파일 처리)
        ↓
[present_files]                → viewer 제공 + 다운로드
```

### 모드 2: 자동화 시스템 구축 (요청 시) — 독립 실행 코드 생성
- 사용자 환경(로컬 PC, GitHub Actions)에서 실행될 **독립적인 Python 스크립트**를 생성한다.
- 이 코드는 컨테이너 밖에서 실행되므로 `requests`, `feedparser` 등 HTTP 라이브러리를 자유롭게 사용한다.
- `automation_builder.py`가 zip 패키지를 생성한다.

```
[automation_builder.py] → 독립 실행 가능한 Python + GitHub Actions 코드 zip 생성
                          (사용자 PC / GitHub Actions에서 실행 → 네트워크 자유)
```

**중요: `scripts/collector.py`는 모드2 자동화 패키지의 레퍼런스 코드이다. 모드1에서는 절대 실행하지 않는다.**

---

## 핵심 동작 방식

### 모드 1: 즉시 실행 (기본)
사용자가 키워드를 던지면 그 자리에서 **수집 → 분석 → .md 보고서 생성 → viewer 제공**.
- 예: "요즘 화장품 트렌드 검색해줘" → 바로 보고서 생성
- **수집은 반드시 Claude의 web_search / WebFetch 도구를 사용한다.**

### 모드 2: 자동화 시스템 구축 (요청 시)
사용자가 "이걸 자동화하고 싶어", "매일 돌리게 해줘" 같은 요청을 하면:
- Python 수집/분석 스크립트 (독립 실행 가능, requests/feedparser 사용)
- GitHub Actions workflow yaml
- config.yaml 템플릿
- README.md (설치/실행 가이드)
를 zip으로 묶어서 제공.

---

## 절대 규칙

**코드 생성, 파일 생성, 스크립트 실행 전에 반드시 아래 확인을 완료하라.**

1. 사용자의 **분야/키워드**를 반드시 확인한다.
   - $ARGUMENTS가 있으면 그것을 사용.
   - 없으면 반드시 질문한다.
2. 사용자가 "알아서 해줘"라고 해도, 최소한 **키워드** 1개는 반드시 확인한다.
3. config.yaml 내 API 키가 비어있는 소스는 **절대 호출하지 않는다**.
4. 웹 스크래핑 시 robots.txt를 반드시 확인하고, 공개 데이터만 수집한다.
5. 부동산/금융 보고서에서 "매수/매도 추천" 같은 투자 조언은 절대 하지 않는다.
   - 대신 "현재 시장 신호", "데이터가 보여주는 것" 중심으로 작성한다.
6. **모드1에서 Python으로 HTTP 요청(requests, feedparser, urllib 등)을 절대 실행하지 않는다.**
   - 데이터 수집은 반드시 Claude 내장 도구(web_search, WebFetch)를 사용한다.
   - Python은 수집된 데이터의 분석과 보고서 생성에만 사용한다.

---

## Step 1: 사용자 확인 (반드시 먼저 실행)

스킬 호출 즉시 아래를 확인한다. $ARGUMENTS가 있으면 해당 항목은 건너뛴다.

**질문 목록 (한 번의 메시지로 모두 질문):**

1. **키워드/분야** — "어떤 분야의 트렌드를 분석할까요? (예: 화장품, 반도체, AI Agent, 부동산, 인디게임)"
2. **깊이** — "간단 요약 vs 심층 분석 중 어떤 걸 원하세요?" (기본: 심층 분석)
3. **추가 관심사** — "특별히 더 알고 싶은 세부 주제가 있나요? (예: 특정 브랜드, 특정 지역, 특정 기술)"

---

## Step 2: Domain 감지 + Config 로드

1. 사용자 키워드로 가장 적합한 domain profile을 자동 매칭한다.
   - 매칭 로직: 키워드 → `domain_profiles/*.yaml`의 `keywords` 필드와 비교
   - 매칭 안 되면 "general" 모드로 동작 (웹검색 중심)
2. `config.yaml`을 로드하여 사용 가능한 API 키를 확인한다.
3. API 키가 있는 소스만 sources 목록에 포함한다.
   - 키가 하나도 없어도 무료 소스(RSS, 웹검색)만으로 동작해야 한다.

**Domain Profile 위치:** 이 스킬 디렉토리의 `domain_profiles/` 폴더

| Domain | 파일 | 트리거 키워드 예시 |
|--------|------|--------------------|
| finance | `finance.yaml` | 주식, 금융, 투자, 반도체, 코스피 |
| beauty | `beauty.yaml` | 화장품, 뷰티, 스킨케어, K-뷰티 |
| tech | `tech.yaml` | AI, IT, 스타트업, MCP, LLM |
| food | `food.yaml` | 요리, 식품, 레시피, 비건, 저당 |
| realestate | `realestate.yaml` | 부동산, 아파트, 전세, 청약 |
| game | `game.yaml` | 게임, 인디게임, 스팀, RPG |

---

## Step 3: 데이터 수집 (Claude 내장 도구 사용)

**반드시 Claude의 web_search / WebFetch 도구로 수집한다. Python HTTP 라이브러리 사용 금지.**

### 수집 순서:

1. **domain profile의 `sources.free` 목록을 읽는다.**

2. **web_search 소스 수집:**
   - domain profile의 `sources.free` 중 `type: web_search`인 항목의 `query_template`에서 `{keyword}`를 실제 키워드로 치환한다.
   - Claude의 `web_search` 도구로 검색하고 결과를 수집한다.
   - 키워드 확장(`keyword_expansion` 규칙)에 따라 연관 키워드로도 추가 검색한다.

3. **RSS 소스 수집:**
   - domain profile의 `sources.free` 중 `type: rss`인 항목의 URL을 `WebFetch` 도구로 가져온다.
   - WebFetch가 RSS XML을 가져오면, Claude가 직접 파싱하거나, 내용을 JSON으로 정리한다.

4. **유료 API 소스 (config에 API 키가 있는 경우만):**
   - config.yaml의 `api_keys`에 값이 있는 소스만 호출한다.
   - `Bash(curl ...)` 명령으로 API를 호출한다. (**Python requests 사용 금지**)
   - 예: `curl -s "https://newsapi.org/v2/everything?q=keyword&apiKey=KEY"`

5. **수집 결과 저장:**
   - 수집된 모든 데이터를 아래 JSON 형식으로 `/mnt/user-data/outputs/collected_data.json`에 저장한다.

```json
[
  {
    "source": "소스명",
    "status": "success",
    "data": [
      {
        "title": "기사/글 제목",
        "link": "URL",
        "summary": "요약 또는 본문 일부",
        "published": "YYYY-MM-DD",
        "source_type": "web_search | rss | api"
      }
    ]
  }
]
```

### 에러 핸들링:
- 각 소스는 **독립적**으로 수집. 하나가 실패해도 나머지는 계속 수집.
- web_search/WebFetch 실패 시 해당 소스를 skip하고 다음 소스로 진행.
- 수집 결과가 3건 미만이면 보고서에 "데이터 불충분 - 키워드를 조정해보세요" 안내 포함.
- 보고서 말미에 "제외된 소스: [소스명] (사유: 연결 실패 / 키 미설정)" 명시.

---

## Step 4: 분석 (Python 로컬 실행)

Step 3에서 저장한 `collected_data.json`을 Python `analyzer.py`로 분석한다.

```bash
python analyzer.py /mnt/user-data/outputs/collected_data.json [keyword]
```

분석 결과는 `analysis_result.json`으로 저장된다.

공통 분석 항목:
- **키워드 빈도 분석**: 수집된 데이터에서 가장 많이 언급된 키워드/엔티티 추출
- **시점별 분류**: 과거(6개월~1년), 현재(최근 1~3개월), 미래(전망)
- **센티먼트 판단**: 긍정/부정/중립 논조 비율
- **이상 신호 탐지**: 급격한 변화, 이례적 패턴

분야별 추가 분석은 각 domain profile의 framework를 따른다.

---

## Step 5: 보고서 생성 (Python 로컬 실행)

분석 결과 JSON과 수집 데이터 JSON을 기반으로 보고서를 생성한다.

```bash
python report_generator.py /mnt/user-data/outputs/collected_data.json /mnt/user-data/outputs/analysis_result.json [keyword] [domain]
```

반드시 아래 템플릿 구조를 따른다. (`templates/report_template.md` 참조)

### 보고서 구조:

```
# [키워드] 트렌드 리서치 보고서
> 생성일 / 분석 키워드 / 데이터 소스 / 제외된 소스

## 핵심 요약 (Executive Summary)
## 1. 과거 동향 (Past Trends) — 최근 6개월~1년
## 2. 현재 트렌드 (Current Trends) — 최근 1~3개월
## 3. 향후 전망 (Future Outlook) — 향후 3~6개월
## 4. 분야별 심화 분석 — domain profile 기반 동적 생성
## 참고 자료 및 출처
## 분석 메타데이터
```

### 보고서 저장 및 제공:

1. `/mnt/user-data/outputs/` 에 `{keyword}_trend_report_{YYYYMMDD}.md` 형태로 저장
2. `present_files` 도구로 viewer 제공 + 다운로드 가능하게
3. config.yaml에 `output_dir`이 설정되어 있으면 해당 경로에도 추가 저장

---

## Step 6: (모드2) 자동화 코드 생성 — 사용자 요청 시에만

사용자가 "자동화", "매일 돌려줘", "파이프라인 만들어줘", "GitHub Actions" 등을 언급하면 실행.

**이 모드에서 생성되는 코드는 사용자 환경(로컬 PC, GitHub Actions)에서 실행되므로
requests, feedparser 등 HTTP 라이브러리를 자유롭게 사용한다.**

생성물:
1. `data_pipeline/` 디렉토리에 Python 수집/분석 스크립트
2. `data_pipeline/.github/workflows/daily_collect.yml` — GitHub Actions cron
3. `data_pipeline/config.yaml` — 사용자가 채울 설정 파일
4. `data_pipeline/README.md` — 설치/실행 가이드
5. 전체를 zip으로 묶어서 `/mnt/user-data/outputs/`에 저장 + present_files로 제공

GitHub Actions 템플릿 핵심:
- cron: '0 9 * * *' (매일 오전 9시)
- 환경변수로 API 키 주입 (GitHub Secrets 사용)
- Slack webhook 알림 (선택사항)

---

## 기존 스킬과의 관계

- **content-research**: 콘텐츠 아이디어/주제 추천에 특화. data-collector는 "시장 분석", "트렌드 리서치", "데이터 기반 보고서" 요청에 트리거.
- **content-repurpose**: 이미 만들어진 콘텐츠를 다른 플랫폼용으로 변환. 역할이 완전히 다르므로 충돌 없음.
- **doc-automation**: PPT/이메일 자동 생성. data-collector의 보고서 결과를 doc-automation으로 넘겨 PPT로 만드는 워크플로는 가능하지만, 별도 요청 시에만.
