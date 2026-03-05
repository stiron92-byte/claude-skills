# 🔧 Claude Code 스킬 제작 요청: data-collector

## 목표

`/mnt/skills/user/data-collector/` 경로에 **데이터 수집 → 분석 → 트렌드 보고서 생성** 스킬을 만들어줘.

사용자가 "요즘 화장품 트렌드 알려줘", "반도체 시장 분석해줘", "인디게임 뭐가 뜨고 있어?" 같은 질문을 하면, 관련 데이터를 자동 수집하고, 분석해서, **과거 → 현재 → 미래 예측** 구조의 트렌드 리서치 보고서를 `.md` 파일로 생성 + viewer 제공 + 다운로드 가능하게 하는 스킬이야.

---

## 핵심 동작 방식: C안 (즉시 실행 + 자동화 코드 생성)

### 모드 1: 즉시 실행 (기본)
사용자가 키워드를 던지면 그 자리에서 **수집 → 분석 → .md 보고서 생성 → viewer 제공**.
- 예: "요즘 화장품 트렌드 검색해줘" → 바로 보고서 생성

### 모드 2: 자동화 시스템 구축 (요청 시)
사용자가 "이걸 자동화하고 싶어", "매일 돌리게 해줘" 같은 요청을 하면:
- Python 수집/분석 스크립트
- GitHub Actions workflow yaml
- config.yaml 템플릿
- README.md (설치/실행 가이드)
를 zip으로 묶어서 제공.

---

## 스킬 디렉토리 구조

```
/mnt/skills/user/data-collector/
├── SKILL.md                          # 메인 스킬 파일
├── config.yaml                       # 사용자 설정 템플릿
├── domain_profiles/                  # 분야별 프로필 (YAML)
│   ├── finance.yaml
│   ├── beauty.yaml
│   ├── tech.yaml
│   ├── food.yaml
│   ├── realestate.yaml
│   └── game.yaml
├── scripts/
│   ├── collector.py                  # 데이터 수집 엔진
│   ├── analyzer.py                   # 분석 엔진
│   ├── report_generator.py           # 보고서 생성
│   ├── automation_builder.py         # 모드2: 자동화 코드 생성
│   ├── requirements.txt
│   └── utils.py                      # 공통 유틸 (에러핸들링, 로깅 등)
├── templates/
│   ├── report_template.md            # 보고서 마크다운 템플릿
│   ├── github_actions_template.yml   # GitHub Actions 템플릿 (모드2용)
│   └── config.example.yaml           # config 예시
└── references/
    └── SETUP-GUIDE.md                # 사용자 가이드
```

---

## SKILL.md 작성 요구사항

### frontmatter

```yaml
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
allowed-tools: Bash(python *) Bash(pip *) Bash(mkdir *) Bash(cp *) Bash(cat *) Bash(curl *)
argument-hint: "[키워드 또는 분야: 화장품/반도체/AI/부동산/인디게임 등]"
---
```

### 절대 규칙

```
## ⛔ 절대 규칙

**코드 생성, 파일 생성, 스크립트 실행 전에 반드시 아래 확인을 완료하라.**

1. 사용자의 **분야/키워드**를 반드시 확인한다. 
   - $ARGUMENTS가 있으면 그것을 사용.
   - 없으면 반드시 질문한다.
2. 사용자가 "알아서 해줘"라고 해도, 최소한 **키워드** 1개는 반드시 확인한다.
3. config.yaml 내 API 키가 비어있는 소스는 **절대 호출하지 않는다**.
4. 웹 스크래핑 시 robots.txt를 반드시 확인하고, 공개 데이터만 수집한다.
5. 부동산/금융 보고서에서 "매수/매도 추천" 같은 투자 조언은 절대 하지 않는다.
   - 대신 "현재 시장 신호", "데이터가 보여주는 것" 중심으로 작성한다.
```

### Step별 흐름

```
## Step 1: 사용자 확인 (반드시 먼저 실행)

스킬 호출 즉시 아래를 확인한다. $ARGUMENTS가 있으면 해당 항목은 건너뛴다.

**질문 목록 (한 번의 메시지로 모두 질문):**

1. **키워드/분야** — "어떤 분야의 트렌드를 분석할까요? (예: 화장품, 반도체, AI Agent, 부동산, 인디게임)"
2. **깊이** — "간단 요약 vs 심층 분석 중 어떤 걸 원하세요?" (기본: 심층 분석)
3. **추가 관심사** — "특별히 더 알고 싶은 세부 주제가 있나요? (예: 특정 브랜드, 특정 지역, 특정 기술)"


## Step 2: Domain 감지 + Config 로드

1. 사용자 키워드로 가장 적합한 domain profile을 자동 매칭한다.
   - 매칭 로직: 키워드 → domain_profiles/*.yaml의 `keywords` 필드와 비교
   - 매칭 안 되면 "general" 모드로 동작 (웹검색 중심)
2. config.yaml을 로드하여 사용 가능한 API 키를 확인한다.
3. API 키가 있는 소스만 sources 목록에 포함한다.
   - 키가 하나도 없어도 무료 소스(RSS, 웹검색)만으로 동작해야 한다.


## Step 3: 데이터 수집

수집 순서:
1. **무료 소스 먼저** — RSS 피드 수집 + 웹검색 (Claude 내장 web_search 활용)
2. **유료 소스** — config에 API 키가 있는 소스만 호출
3. **키워드 자동 확장** — domain profile의 keyword_expansion 규칙에 따라 연관 키워드도 수집

에러 핸들링:
- 각 소스는 **독립적**으로 실행. 하나가 실패해도 나머지는 계속 수집.
- API 호출 실패 시 **최대 2회 재시도** (2초 간격). 3회 연속 실패하면 skip + 로그 기록.
- 수집 결과가 3건 미만이면 보고서에 "데이터 불충분 - 키워드를 조정해보세요" 안내 포함.
- 보고서 말미에 "제외된 소스: [소스명] (사유: rate limit / 키 미설정 / 연결 실패)" 명시.


## Step 4: 분석

domain profile의 `analysis.framework`에 정의된 분석 방식을 적용한다.

공통 분석 항목:
- **키워드 빈도 분석**: 수집된 데이터에서 가장 많이 언급된 키워드/엔티티 추출
- **시점별 분류**: 과거(6개월~1년), 현재(최근 1~3개월), 미래(전망)
- **센티먼트 판단**: 긍정/부정/중립 논조 비율
- **이상 신호 탐지**: 급격한 변화, 이례적 패턴

분야별 추가 분석은 각 domain profile의 framework를 따른다.


## Step 5: 보고서 생성

반드시 아래 템플릿 구조를 따른다.

### 보고서 템플릿:

```markdown
# [키워드] 트렌드 리서치 보고서

> 📅 생성일: YYYY-MM-DD  
> 🔍 분석 키워드: [키워드]  
> 📊 데이터 소스: [사용된 소스 목록]  
> ⚠️ 제외된 소스: [제외된 소스 + 사유]

---

## 📌 핵심 요약 (Executive Summary)
- 3~5줄로 핵심만 요약
- 가장 중요한 발견 1가지를 맨 첫 줄에

---

## 1. 과거 동향 (Past Trends)
**기간: 최근 6개월 ~ 1년**

### 주요 흐름
- [트렌드 1]: 설명 + 근거 데이터/출처
- [트렌드 2]: 설명 + 근거 데이터/출처

### 주요 이벤트 타임라인
| 시기 | 이벤트 | 영향 |
|------|--------|------|
| YYYY.MM | 이벤트 내용 | 영향 설명 |

---

## 2. 현재 트렌드 (Current Trends)
**기간: 최근 1~3개월**

### 지금 가장 뜨는 것
1. **[키워드/제품/기술]** — 설명 + 근거
2. **[키워드/제품/기술]** — 설명 + 근거
3. **[키워드/제품/기술]** — 설명 + 근거

### 데이터가 말하는 것
- [수치 기반 인사이트]
- [비교 분석 결과]

---

## 3. 향후 전망 (Future Outlook)
**기간: 향후 3~6개월**

### 예측
1. **[전망 1]** — 예측 내용
   - 📊 근거: [데이터/업계 동향/전문가 의견]
2. **[전망 2]** — 예측 내용  
   - 📊 근거: [데이터/업계 동향/전문가 의견]

### 주목할 신호 (Watch List)
- [아직 초기이지만 주목할 움직임]
- [잠재적 게임 체인저]

### ⚠️ 리스크 요인
- [트렌드를 바꿀 수 있는 리스크]

---

## 4. 분야별 심화 분석
(domain profile의 highlight_sections에 따라 동적 생성)

---

## 📚 참고 자료 및 출처
| 출처 | 제목 | 날짜 | URL |
|------|------|------|-----|
| 출처명 | 기사/보고서 제목 | YYYY-MM-DD | URL |

---

## ℹ️ 분석 메타데이터
- 총 수집 데이터: N건
- 사용된 소스: [소스 목록]
- 분석 소요 시간: N초
- 키워드 확장: [원본 키워드] → [확장된 키워드 목록]
```

### 보고서 저장 및 제공:

1. `/mnt/user-data/outputs/` 에 `{keyword}_trend_report_{YYYYMMDD}.md` 형태로 저장
2. `present_files` 도구로 viewer 제공 + 다운로드 가능하게
3. config.yaml에 `output_dir`이 설정되어 있으면 해당 경로에도 추가 저장


## Step 6: (모드2) 자동화 코드 생성 — 사용자 요청 시에만

사용자가 "자동화", "매일 돌려줘", "파이프라인 만들어줘", "GitHub Actions" 등을 언급하면 실행.

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
```

---

## config.yaml 설계

```yaml
# data-collector 스킬 설정 파일
# 비어있는 값은 해당 기능을 사용하지 않음을 의미합니다.

# ── 보고서 설정 ──
output_dir: ""                    # 추가 저장 경로 (비워두면 기본 경로만 사용)
report_language: "ko"             # ko / en
report_depth: "deep"              # deep (심층분석) / brief (간단요약)

# ── API 키 (선택사항) ──
# 키가 없는 소스는 자동으로 제외되고, 무료 소스만으로 동작합니다.
api_keys:
  newsapi: ""                     # https://newsapi.org 에서 발급
  data_go_kr: ""                  # https://www.data.go.kr 에서 발급  
  fred: ""                        # https://fred.stlouisfed.org/docs/api/api_key.html
  youtube_data: ""                # Google Cloud Console에서 YouTube Data API v3 키 발급
  steam: ""                       # https://steamcommunity.com/dev/apikey

# ── MCP 연동 (선택사항, 모드2 자동화용) ──
integrations:
  slack_webhook: ""               # Slack Incoming Webhook URL
  
# ── 기본 분야 설정 (선택사항) ──
# 설정하면 매번 분야를 묻지 않고 해당 분야로 바로 실행
default_domain: ""                # finance / beauty / tech / food / realestate / game
```

---

## Domain Profile 상세 설계

각 domain profile은 아래 YAML 구조를 따른다. 6개 파일을 모두 만들어줘.

### 공통 YAML 스키마

```yaml
domain: "[domain_id]"
display_name: "[표시명]"

# 이 도메인으로 매칭할 키워드 목록
keywords:
  - "키워드1"
  - "키워드2"

sources:
  # 항상 사용 (API 키 불필요)
  free:
    - type: rss | web_search
      name: "[소스명]"
      url: "[URL]"                    # type: rss일 때만
      query_template: "[검색 템플릿]"  # type: web_search일 때만. {keyword}를 플레이스홀더로 사용
      priority: 1                      # 낮을수록 먼저 수집
  
  # API 키가 있을 때만 사용
  paid:
    - type: api
      name: "[소스명]"
      requires_key: "[config.yaml의 api_keys 중 해당 키 이름]"
      query_template: "[검색 쿼리 템플릿]"

# 키워드 자동 확장 규칙
keyword_expansion:
  rules:
    - type: "[확장 유형]"
      description: "[설명]"
      examples:                        # 대표 예시 (실행 시 Claude가 이 패턴을 참고하여 동적 확장)
        입력키워드: ["확장1", "확장2"]
    - type: seasonal
      description: "현재 월 기준 시즌 키워드 자동 추가"
      mapping:
        spring: ["키워드1", "키워드2"]
        summer: ["키워드1", "키워드2"]
        autumn: ["키워드1", "키워드2"]
        winter: ["키워드1", "키워드2"]

# 분석 프레임워크
analysis:
  framework:
    - name: "[분석 항목명]"
      method: "[분석 방법]"
      description: "[이 분석이 하는 일]"

# 보고서에서 강조할 섹션 (Step 5의 "4. 분야별 심화 분석" 부분에 들어감)
report:
  highlight_sections:
    - "[섹션 제목]"
  tone: "[보고서 톤]"
```

---

### finance.yaml

```yaml
domain: finance
display_name: "금융/투자"

keywords:
  - "주식"
  - "금융"
  - "투자"
  - "증시"
  - "경제"
  - "금리"
  - "환율"
  - "코스피"
  - "나스닥"
  - "S&P"
  - "채권"
  - "ETF"
  - "FOMC"
  - "반도체" 
  - "stock"
  - "finance"
  - "market"

sources:
  free:
    - type: rss
      name: "한국경제 RSS"
      url: "https://www.hankyung.com/feed/all-news"
      priority: 1
    - type: rss
      name: "매일경제 RSS"
      url: "https://www.mk.co.kr/rss/30000001/"
      priority: 2
    - type: rss
      name: "Bloomberg Markets RSS"
      url: "https://feeds.bloomberg.com/markets/news.rss"
      priority: 2
    - type: rss
      name: "SEC EDGAR Company Filings RSS"
      url: "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&dateb=&owner=include&count=20&search_text=&action=getcompany&RSS"
      priority: 3
    - type: web_search
      name: "금융 트렌드 웹검색"
      query_template: "{keyword} 시장 동향 2025"
      priority: 1
    - type: web_search
      name: "경제 지표 검색"
      query_template: "{keyword} 경제지표 전망"
      priority: 2

  paid:
    - type: api
      name: "FRED API"
      requires_key: fred
      query_template: "interest rate, CPI, unemployment, GDP"
    - type: api
      name: "NewsAPI 금융"
      requires_key: newsapi
      query_template: "{keyword} AND (stock OR market OR economy OR finance)"

keyword_expansion:
  rules:
    - type: sector_related
      description: "업종/종목명 → 관련 종목 및 업종 키워드 확장"
      examples:
        반도체: ["삼성전자", "SK하이닉스", "TSMC", "NVIDIA", "파운드리", "HBM", "CHIPS Act"]
        금리: ["FOMC", "기준금리", "국채", "금리인하", "금리인상", "연준"]
        2차전지: ["LG에너지솔루션", "삼성SDI", "CATL", "리튬", "전고체배터리"]
    - type: event_keywords
      description: "시장 이벤트 키워드 자동 포함"
      examples:
        상시: ["실적발표", "IPO", "공시", "M&A"]
    - type: seasonal
      description: "분기별 이벤트 키워드"
      mapping:
        spring: ["1분기 실적", "주주총회", "배당"]
        summer: ["2분기 실적", "반기보고서"]
        autumn: ["3분기 실적", "추경"]
        winter: ["4분기 전망", "내년 경제 전망", "연간 실적"]

analysis:
  framework:
    - name: "가격/지표 변화율"
      method: "time_series_change"
      description: "1개월/3개월/6개월 변화율 계산, 이동평균 비교"
    - name: "거래량 이상 탐지"
      method: "volume_anomaly"
      description: "평균 대비 이상 거래량 구간 탐지"
    - name: "뉴스 센티먼트"
      method: "sentiment_ratio"
      description: "수집된 뉴스의 긍정/부정/중립 비율 변화"
    - name: "매크로 연결"
      method: "macro_correlation"
      description: "관련 경제지표(금리, CPI 등)와의 연관성 분석"
    - name: "이벤트 임팩트"
      method: "event_timeline"
      description: "주요 이벤트(FOMC, 실적발표 등) 전후 시장 반응"

report:
  highlight_sections:
    - "핵심 수치 요약표 (가격, 변화율, 거래량)"
    - "주요 이벤트 타임라인"
    - "업종/종목 비교"
    - "리스크 요인 분석"
  tone: "객관적, 수치 중심, 투자 조언은 절대 하지 않음"
```

---

### beauty.yaml

```yaml
domain: beauty
display_name: "뷰티/화장품"

keywords:
  - "화장품"
  - "뷰티"
  - "스킨케어"
  - "메이크업"
  - "올리브영"
  - "성분"
  - "선크림"
  - "세럼"
  - "K-뷰티"
  - "K-beauty"
  - "skincare"
  - "cosmetics"

sources:
  free:
    - type: rss
      name: "Allure Beauty"
      url: "https://www.allure.com/feed/rss"
      priority: 1
    - type: rss
      name: "Byrdie"
      url: "https://www.byrdie.com/rss"
      priority: 2
    - type: rss
      name: "식약처 공지사항"
      url: "https://www.mfds.go.kr/brd/m_99/rss.do"
      priority: 3
    - type: web_search
      name: "뷰티 트렌드 검색"
      query_template: "{keyword} 트렌드 2025"
      priority: 1
    - type: web_search
      name: "올리브영 트렌드"
      query_template: "올리브영 {keyword} 인기 신제품"
      priority: 1
    - type: web_search
      name: "화해 성분 트렌드"
      query_template: "화해 {keyword} 성분 추천"
      priority: 2
    - type: web_search
      name: "글로벌 뷰티"
      query_template: "K-beauty {keyword} trend global"
      priority: 2

  paid:
    - type: api
      name: "NewsAPI 뷰티"
      requires_key: newsapi
      query_template: "{keyword} AND (beauty OR skincare OR cosmetics OR K-beauty)"
    - type: api
      name: "YouTube 뷰티 트렌드"
      requires_key: youtube_data
      query_template: "{keyword} 뷰티 리뷰"

keyword_expansion:
  rules:
    - type: ingredient_group
      description: "성분명 → 관련 성분군 확장"
      examples:
        레티놀: ["레틴알", "바쿠치올", "비타민A 유도체", "레티노이드"]
        나이아신아마이드: ["비타민B3", "나이아신", "니코틴아마이드"]
        비타민C: ["아스코르빅애씨드", "비타민C 유도체", "AA2G"]
        히알루론산: ["HA", "저분자 히알루론산", "소듐히알루로네이트"]
        세라마이드: ["피부장벽", "지질", "콜레스테롤"]
    - type: brand_competitors
      description: "브랜드 → 같은 카테고리 경쟁 브랜드 확장"
      examples:
        이니스프리: ["아이오페", "한율", "설화수", "라네즈"]
        닥터지: ["메디힐", "CNP", "리얼바리어"]
    - type: seasonal
      description: "현재 월 기준 시즌 키워드 추가"
      mapping:
        spring: ["봄 메이크업", "톤업", "자외선차단 준비", "꽃분증 피부"]
        summer: ["워터프루프", "쿨링", "모공관리", "자외선차단", "선크림 추천"]
        autumn: ["가을 스킨케어", "보습 전환기", "환절기 피부"]
        winter: ["보습", "장벽크림", "건조 피부", "수분크림", "입술 보호"]

analysis:
  framework:
    - name: "성분 트렌드"
      method: "keyword_frequency"
      description: "성분명 언급 빈도 변화 추적, 새로 등장한 성분 발견"
    - name: "브랜드 동향"
      method: "entity_tracking"
      description: "브랜드별 신제품 출시 빈도, 언급량 변화"
    - name: "가격대별 트렌드"
      method: "price_segment"
      description: "럭셔리 vs 로드샵 vs 인디 브랜드 트렌드 비교"
    - name: "글로벌 vs 국내"
      method: "cross_market"
      description: "해외 K-뷰티 반응 vs 국내 트렌드 차이 분석"
    - name: "계절성 분석"
      method: "seasonal_pattern"
      description: "계절에 따른 성분/제품 관심도 변화"

report:
  highlight_sections:
    - "지금 뜨는 성분 TOP 5 (근거 포함)"
    - "주목할 브랜드/제품"
    - "계절별 트렌드 변화"
    - "글로벌 K-뷰티 동향"
  tone: "전문적이되 읽기 쉽게, 실용적 정보 중심"
```

---

### tech.yaml

```yaml
domain: tech
display_name: "테크/IT"

keywords:
  - "IT"
  - "테크"
  - "AI"
  - "인공지능"
  - "스타트업"
  - "개발"
  - "프로그래밍"
  - "SaaS"
  - "클라우드"
  - "MCP"
  - "LLM"
  - "Agent"
  - "tech"
  - "startup"
  - "developer"

sources:
  free:
    - type: rss
      name: "Hacker News (GeekNews 한국어)"
      url: "https://news.hada.io/rss"
      priority: 1
    - type: rss
      name: "요즘IT"
      url: "https://yozm.wishket.com/magazine/feed/"
      priority: 1
    - type: rss
      name: "TechCrunch"
      url: "https://techcrunch.com/feed/"
      priority: 2
    - type: rss
      name: "The Verge"
      url: "https://www.theverge.com/rss/index.xml"
      priority: 2
    - type: rss
      name: "Product Hunt Daily"
      url: "https://www.producthunt.com/feed"
      priority: 2
    - type: rss
      name: "arXiv AI/ML"
      url: "https://rss.arxiv.org/rss/cs.AI"
      priority: 3
    - type: web_search
      name: "기술 트렌드 검색"
      query_template: "{keyword} trend 2025"
      priority: 1
    - type: web_search
      name: "GitHub 트렌딩"
      query_template: "github trending {keyword}"
      priority: 2

  paid:
    - type: api
      name: "NewsAPI 테크"
      requires_key: newsapi
      query_template: "{keyword} AND (technology OR startup OR AI OR software)"
    - type: api
      name: "YouTube 테크 리뷰"
      requires_key: youtube_data
      query_template: "{keyword} 기술 리뷰 개발"

keyword_expansion:
  rules:
    - type: tech_ecosystem
      description: "기술명 → 관련 프레임워크/회사/경쟁 기술 확장"
      examples:
        AI Agent: ["LangChain", "CrewAI", "AutoGen", "Claude Code", "MCP", "Tool Use"]
        MCP: ["Model Context Protocol", "Anthropic MCP", "MCP 서버", "Function Calling"]
        LLM: ["GPT", "Claude", "Gemini", "Llama", "RAG", "Fine-tuning"]
        React: ["Next.js", "Remix", "Vite", "Vue", "Svelte"]
        클라우드: ["AWS", "GCP", "Azure", "Kubernetes", "서버리스"]
    - type: layer_classification
      description: "기술 레이어 분류 키워드 (인프라/플랫폼/앱)"
      examples:
        인프라: ["GPU", "CUDA", "TPU", "데이터센터"]
        플랫폼: ["API", "SDK", "PaaS", "MLOps"]
        앱: ["SaaS", "프로덕트", "UX", "프론트엔드"]
    - type: seasonal
      description: "테크 이벤트 시즌"
      mapping:
        spring: ["Google I/O", "WWDC 준비"]
        summer: ["WWDC", "중간 실적"]
        autumn: ["AWS re:Invent", "GitHub Universe"]
        winter: ["CES", "연간 회고", "내년 전망"]

analysis:
  framework:
    - name: "기술 성숙도"
      method: "hype_cycle"
      description: "Hype 단계 판단: 초기 화제 → 실사용 증가 → 안정화"
    - name: "투자 동향"
      method: "funding_tracking"
      description: "관련 스타트업 펀딩 라운드, 투자 규모"
    - name: "오픈소스 활성도"
      method: "oss_metrics"
      description: "GitHub 스타 증가율, 기여자 수, 포크 수"
    - name: "채택 신호"
      method: "adoption_signal"
      description: "대기업 도입 사례, 채용공고 언급 빈도"
    - name: "경쟁 구도"
      method: "competitive_landscape"
      description: "주요 플레이어 포지셔닝, 차별화 요소"

report:
  highlight_sections:
    - "이번 주/달 핫 프로덕트·기술 TOP 5"
    - "기술 성숙도 판단 + 근거"
    - "개발자가 주목할 것 (실무 관점)"
    - "투자/채용 신호"
  tone: "기술적이되 실무 중심, 과도한 전문용어 회피"
```

---

### food.yaml

```yaml
domain: food
display_name: "요리/식품"

keywords:
  - "요리"
  - "레시피"
  - "식품"
  - "음식"
  - "식재료"
  - "맛집"
  - "건강식"
  - "비건"
  - "저당"
  - "제로슈거"
  - "식단"
  - "cooking"
  - "recipe"
  - "food"

sources:
  free:
    - type: rss
      name: "Serious Eats"
      url: "https://www.seriouseats.com/feeds/serious-eats"
      priority: 1
    - type: rss
      name: "Bon Appétit"
      url: "https://www.bonappetit.com/feed/rss"
      priority: 2
    - type: rss
      name: "Maangchi (한식)"
      url: "https://www.maangchi.com/feed"
      priority: 2
    - type: web_search
      name: "식품 트렌드 검색"
      query_template: "{keyword} 식품 트렌드 2025"
      priority: 1
    - type: web_search
      name: "레시피 트렌드"
      query_template: "{keyword} 인기 레시피 요리법"
      priority: 1
    - type: web_search
      name: "식재료 가격 동향"
      query_template: "{keyword} 식재료 가격 시세"
      priority: 2
    - type: web_search
      name: "건강 식품 트렌드"
      query_template: "{keyword} 건강 웰빙 식품"
      priority: 2

  paid:
    - type: api
      name: "NewsAPI 식품"
      requires_key: newsapi
      query_template: "{keyword} AND (food OR recipe OR cooking OR restaurant)"
    - type: api
      name: "YouTube 쿠킹"
      requires_key: youtube_data
      query_template: "{keyword} 요리 레시피 먹방"

keyword_expansion:
  rules:
    - type: ingredient_related
      description: "식재료/요리법 → 관련 재료·조리법 확장"
      examples:
        저당: ["제로슈거", "알룰로스", "스테비아", "당류저감", "무설탕"]
        비건: ["식물성", "대체육", "두부", "템페", "오트밀크"]
        발효: ["김치", "콤부차", "요거트", "미소", "프로바이오틱스"]
        에어프라이어: ["오븐요리", "그릴", "저유", "간편조리"]
    - type: health_trend
      description: "건강 트렌드 연결"
      examples:
        장건강: ["프로바이오틱스", "프리바이오틱스", "식이섬유", "발효식품"]
        다이어트: ["저탄수화물", "키토", "간헐적단식", "칼로리"]
    - type: seasonal
      description: "제철 식재료 + 시즌 키워드"
      mapping:
        spring: ["봄나물", "냉이", "달래", "쑥", "딸기"]
        summer: ["냉면", "수박", "콩국수", "냉국", "팥빙수"]
        autumn: ["버섯", "고구마", "밤", "감", "새우"]
        winter: ["김장", "국물요리", "탕", "전골", "귤"]

analysis:
  framework:
    - name: "식재료 트렌드"
      method: "keyword_frequency"
      description: "식재료명 언급 빈도 변화, 새로운 재료 발견"
    - name: "건강/웰빙 연결"
      method: "health_correlation"
      description: "영양 트렌드와 식재료 인기도 연결 분석"
    - name: "외식 vs 집밥"
      method: "dining_comparison"
      description: "레스토랑 트렌드 vs 홈쿠킹 트렌드 비교"
    - name: "글로벌 영향"
      method: "cross_cultural"
      description: "해외에서 유입되는 음식 트렌드 (예: 두바이 초콜릿, 탕후루)"
    - name: "가격 동향"
      method: "price_tracking"
      description: "주요 식재료 가격 변동 추이"

report:
  highlight_sections:
    - "지금 뜨는 식재료·요리법 TOP 5"
    - "제철 식재료 활용 가이드"
    - "건강 트렌드와 식품 연결"
    - "글로벌 → 한국 유입 트렌드"
  tone: "친근하고 실용적, 바로 활용 가능한 정보 중심"
```

---

### realestate.yaml

```yaml
domain: realestate
display_name: "부동산"

keywords:
  - "부동산"
  - "아파트"
  - "전세"
  - "월세"
  - "매매"
  - "분양"
  - "청약"
  - "재건축"
  - "재개발"
  - "실거래가"
  - "집값"
  - "주택"
  - "오피스텔"

sources:
  free:
    - type: rss
      name: "머니투데이 부동산"
      url: "https://news.mt.co.kr/newsList.html?type=rss&pDepth=news&pDepth2=real"
      priority: 1
    - type: web_search
      name: "부동산 시장 동향"
      query_template: "{keyword} 부동산 시세 동향 2025"
      priority: 1
    - type: web_search
      name: "부동산 정책"
      query_template: "{keyword} 부동산 정책 규제 대출"
      priority: 1
    - type: web_search
      name: "실거래가 검색"
      query_template: "{keyword} 아파트 실거래가 매매"
      priority: 2
    - type: web_search
      name: "청약/분양 정보"
      query_template: "{keyword} 분양 청약 일정"
      priority: 2
    - type: web_search
      name: "한국은행 금리"
      query_template: "한국은행 기준금리 주담대 금리"
      priority: 2

  paid:
    - type: api
      name: "공공데이터포털 실거래가"
      requires_key: data_go_kr
      query_template: "아파트 실거래가 조회"
    - type: api
      name: "NewsAPI 부동산"
      requires_key: newsapi
      query_template: "{keyword} AND (부동산 OR apartment OR real estate OR housing)"

keyword_expansion:
  rules:
    - type: region_adjacent
      description: "지역명 → 인접 지역 + 행정구역 확장"
      examples:
        강남: ["서초", "송파", "강남3구", "강남역", "압구정", "대치"]
        마포: ["용산", "서대문", "마포구", "합정", "상수", "연남"]
        판교: ["분당", "성남", "위례", "수지", "동탄"]
        제주: ["서귀포", "제주시", "제주도", "제주 이주"]
    - type: policy_keywords
      description: "부동산 정책 관련 키워드 자동 포함"
      examples:
        대출: ["DSR", "LTV", "DTI", "특례보금자리론", "디딤돌대출"]
        세금: ["종부세", "양도세", "취득세", "보유세"]
        규제: ["투기과열지구", "조정대상지역", "분양가상한제"]
    - type: seasonal
      description: "부동산 시즌 키워드"
      mapping:
        spring: ["봄 이사 시즌", "3월 분양", "입학 수요"]
        summer: ["여름 비수기", "하반기 분양"]
        autumn: ["가을 이사 시즌", "9월 분양", "추석 전후"]
        winter: ["연말 실거래", "내년 입주물량", "내년 부동산 전망"]

analysis:
  framework:
    - name: "가격 추이"
      method: "price_trend"
      description: "매매/전세 가격 변화율, 매매-전세 갭 분석"
    - name: "거래량 분석"
      method: "volume_analysis"
      description: "전월 대비, 전년 동기 대비 거래량 변화"
    - name: "정책 영향"
      method: "policy_impact"
      description: "최근 규제/완화 정책과 시장 반응 분석"
    - name: "수급 분석"
      method: "supply_demand"
      description: "입주물량, 인허가, 미분양 추이"
    - name: "금리 연결"
      method: "interest_rate_correlation"
      description: "기준금리/주담대 금리 변화와 시장 영향"

report:
  highlight_sections:
    - "지역별 가격 변동 요약표"
    - "주요 정책 변화 타임라인"
    - "수급 현황 (입주물량, 미분양)"
    - "금리 환경과 시장 영향"
  tone: "객관적 데이터 중심, 매수/매도 추천 절대 불가, '시장 신호' 중심 서술"
```

---

### game.yaml

```yaml
domain: game
display_name: "게임"

keywords:
  - "게임"
  - "인디게임"
  - "스팀"
  - "Steam"
  - "닌텐도"
  - "플스"
  - "Xbox"
  - "신작"
  - "할인"
  - "소울라이크"
  - "RPG"
  - "게임 추천"
  - "game"
  - "gaming"
  - "e스포츠"

sources:
  free:
    - type: rss
      name: "IGN RSS"
      url: "https://feeds.feedburner.com/ign/all"
      priority: 1
    - type: rss
      name: "Kotaku"
      url: "https://kotaku.com/rss"
      priority: 2
    - type: web_search
      name: "게임 트렌드 검색"
      query_template: "{keyword} 게임 트렌드 신작 2025"
      priority: 1
    - type: web_search
      name: "스팀 인기"
      query_template: "Steam 인기 게임 {keyword} 동시접속"
      priority: 1
    - type: web_search
      name: "게임 커뮤니티 반응"
      query_template: "{keyword} 게임 리뷰 평가 커뮤니티"
      priority: 2
    - type: web_search
      name: "게임 할인"
      query_template: "{keyword} 게임 할인 세일 최저가"
      priority: 2

  paid:
    - type: api
      name: "Steam Web API"
      requires_key: steam
      query_template: "게임 정보, 동시접속자, 리뷰"
    - type: api
      name: "NewsAPI 게임"
      requires_key: newsapi
      query_template: "{keyword} AND (game OR gaming OR esports OR indie)"
    - type: api
      name: "YouTube 게임"
      requires_key: youtube_data
      query_template: "{keyword} 게임 리뷰 실황 공략"

keyword_expansion:
  rules:
    - type: genre_titles
      description: "장르명 → 대표 타이틀 + 관련 장르 확장"
      examples:
        소울라이크: ["엘든링", "다크소울", "블랙미스", "Lies of P", "하데스"]
        메타버스: ["로블록스", "제페토", "VRChat", "포트나이트"]
        인디게임: ["스팀 인디", "인디 추천", "독립 개발", "게임잼"]
        FPS: ["발로란트", "오버워치", "카운터스트라이크", "에이펙스"]
    - type: platform_keywords
      description: "플랫폼 관련 키워드"
      examples:
        PC: ["Steam", "Epic", "GOG"]
        콘솔: ["PS5", "Xbox Series", "닌텐도 스위치2"]
        모바일: ["iOS", "Android", "모바일게임"]
    - type: seasonal
      description: "게임 이벤트 시즌"
      mapping:
        spring: ["봄 세일", "GDC"]
        summer: ["Steam 여름 세일", "Summer Game Fest"]
        autumn: ["도쿄게임쇼", "가을 신작"]
        winter: ["Steam 겨울 세일", "The Game Awards", "연말 GOTY"]

analysis:
  framework:
    - name: "인기도 추이"
      method: "popularity_tracking"
      description: "동시접속자 추이, 스팀 리뷰 비율 변화"
    - name: "신작 동향"
      method: "new_release_tracking"
      description: "출시 예정작, 얼리억세스 반응, 기대작"
    - name: "커뮤니티 반응"
      method: "community_sentiment"
      description: "긍정/부정 여론, 화제 이슈, 논란"
    - name: "할인/가격"
      method: "price_tracking"
      description: "역대 최저가, 현재 할인, 번들 정보"
    - name: "장르 트렌드"
      method: "genre_analysis"
      description: "뜨는 장르, 식는 장르, 하이브리드 장르"

report:
  highlight_sections:
    - "이번 주/달 주목할 게임 TOP 5"
    - "할인 정보 요약"
    - "출시 예정작 캘린더"
    - "장르 트렌드 변화"
  tone: "게이머 친화적, 재미있되 정보 밀도 높게"
```

---

## 에러 핸들링 정책 (scripts/utils.py에 구현)

```python
"""
에러 핸들링 정책:
1. 소스별 독립 실행: 하나가 실패해도 나머지 계속 수집
2. 재시도: API 호출 실패 시 최대 2회 재시도, 2초 간격
3. 3회 연속 실패 → skip + 로그에 기록
4. 수집 결과 3건 미만 → 보고서에 "데이터 불충분" 안내
5. 보고서 말미에 제외된 소스 + 사유 명시

구현 패턴:
"""
import time
import logging

MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds
MIN_DATA_THRESHOLD = 3

def fetch_with_retry(fetch_func, source_name, *args, **kwargs):
    """소스별 독립 실행 + 재시도 로직"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = fetch_func(*args, **kwargs)
            return {"status": "success", "source": source_name, "data": result}
        except Exception as e:
            if attempt < MAX_RETRIES:
                logging.warning(f"[{source_name}] 시도 {attempt+1} 실패: {e}. {RETRY_DELAY}초 후 재시도...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"[{source_name}] 최종 실패: {e}")
                return {"status": "failed", "source": source_name, "reason": str(e)}
```

---

## 기존 스킬과의 관계

- `content-research` 스킬: 콘텐츠 아이디어/주제 추천에 특화. **data-collector와 겹치지 않게**, content-research는 "유튜브 주제 뭐 할까?", "블로그 글감 추천" 같은 콘텐츠 기획에, data-collector는 "시장 분석", "트렌드 리서치", "데이터 기반 보고서" 요청에 트리거되게 한다.
- `content-repurpose` 스킬: 이미 만들어진 콘텐츠를 다른 플랫폼용으로 변환. 역할이 완전히 다르므로 충돌 없음.
- `doc-automation` 스킬: PPT/이메일 자동 생성. data-collector의 보고서 결과를 doc-automation으로 넘겨 PPT로 만드는 워크플로는 가능하지만, 이건 별도 요청 시에만.

---

## 테스트 케이스 (스킬 완성 후 검증)

1. **"요즘 화장품 트렌드 검색해줘"** → beauty 프로필 자동 감지, 무료 소스만으로 보고서 생성, .md 파일 viewer 제공
2. **"반도체 시장 분석해줘"** → finance 프로필 감지, "반도체" 키워드 확장 적용, 수치 중심 보고서
3. **"인디게임 뭐가 뜨고 있어?"** → game 프로필 감지, 게이머 톤의 보고서
4. **"AI Agent 기술 동향 파악해줘"** → tech 프로필 감지, 기술 성숙도 분석 포함
5. **"저당 식품 트렌드 알려줘"** → food 프로필 감지, 건강 트렌드 연결 분석
6. **"강남 아파트 시장 어때?"** → realestate 프로필 감지, 투자 조언 없는 시장 신호 중심
7. **"이걸 매일 자동으로 돌리고 싶어"** → 모드2 전환, 자동화 코드 zip 생성
8. **"블록체인 트렌드 알려줘"** → 매칭되는 프로필 없음 → general 모드(웹검색 중심)로 동작

---

## 최종 점검 사항

- [ ] SKILL.md frontmatter의 description이 충분히 다양한 트리거를 포함하는가
- [ ] config.yaml 없이(기본값만으로) 스킬이 정상 동작하는가
- [ ] API 키가 하나도 없어도 무료 소스만으로 유의미한 보고서가 생성되는가
- [ ] 각 domain profile의 RSS URL이 실제로 접근 가능한가 (404 체크)
- [ ] 보고서 .md가 `/mnt/user-data/outputs/`에 저장되고 present_files로 제공되는가
- [ ] 금융/부동산 보고서에서 투자 조언이 포함되지 않는가
- [ ] 에러 발생 시 전체 파이프라인이 멈추지 않고 부분 결과라도 제공하는가
- [ ] 모드2에서 생성된 zip 파일에 README.md가 포함되어 있는가
