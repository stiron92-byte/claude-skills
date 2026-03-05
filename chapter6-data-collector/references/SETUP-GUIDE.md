# data-collector 스킬 설정 가이드

## 개요

data-collector 스킬은 관심 분야의 데이터를 자동 수집하고 분석하여 트렌드 리서치 보고서를 생성합니다.

## 기본 사용법

API 키 없이도 무료 소스(RSS 피드, 웹검색)만으로 바로 사용 가능합니다.

```
/data-collector 화장품
/data-collector AI Agent
/data-collector 부동산
```

## API 키 설정 (선택사항)

더 풍부한 데이터를 수집하려면 API 키를 설정하세요.

### 1. NewsAPI
- 발급: https://newsapi.org/register
- 무료 플랜: 일 100건 (개발용)
- config.yaml의 `api_keys.newsapi`에 입력

### 2. 공공데이터포털 (부동산 실거래가 등)
- 발급: https://www.data.go.kr
- 회원가입 후 활용신청
- config.yaml의 `api_keys.data_go_kr`에 입력

### 3. FRED API (미국 경제지표)
- 발급: https://fred.stlouisfed.org/docs/api/api_key.html
- 무료
- config.yaml의 `api_keys.fred`에 입력

### 4. YouTube Data API v3
- 발급: Google Cloud Console > API 및 서비스 > YouTube Data API v3
- 무료 일일 할당량: 10,000 유닛
- config.yaml의 `api_keys.youtube_data`에 입력

### 5. Steam Web API (게임 분석용)
- 발급: https://steamcommunity.com/dev/apikey
- Steam 계정 필요
- config.yaml의 `api_keys.steam`에 입력

## 지원 도메인

| 도메인 | 트리거 키워드 예시 |
|--------|-------------------|
| finance (금융/투자) | 주식, 반도체, 코스피, ETF, 금리 |
| beauty (뷰티/화장품) | 화장품, 스킨케어, K-뷰티, 올리브영 |
| tech (테크/IT) | AI, LLM, MCP, 스타트업, SaaS |
| food (요리/식품) | 레시피, 비건, 저당, 식재료 |
| realestate (부동산) | 아파트, 전세, 청약, 분양, 실거래가 |
| game (게임) | 스팀, 인디게임, RPG, e스포츠 |

매칭되는 도메인이 없으면 자동으로 웹검색 중심의 general 모드로 동작합니다.

## 자동화 (모드2)

보고서 생성 후 "이걸 자동화하고 싶어"라고 말하면:
- Python 수집/분석 스크립트
- GitHub Actions workflow
- config 템플릿
- README

를 zip으로 묶어 제공합니다.

### GitHub Actions 설정

1. 생성된 zip을 GitHub 저장소에 push
2. Settings > Secrets and variables > Actions에서 환경변수 추가:
   - `NEWSAPI_KEY` (선택)
   - `SLACK_WEBHOOK_URL` (선택)
3. 매일 오전 9시(UTC)에 자동 수집/보고서 생성
4. Actions 탭에서 수동 실행도 가능

## 주의사항

- 금융/부동산 보고서에는 투자 조언이 포함되지 않습니다.
- 웹 스크래핑 시 robots.txt를 준수하며, 공개 데이터만 수집합니다.
- API 호출 실패 시 최대 2회 재시도 후 해당 소스를 건너뜁니다.
- 수집 데이터가 3건 미만이면 보고서에 안내 메시지가 포함됩니다.
