# outline.json 형식

build_deck.py와 verify_deck.py가 읽는 보고 설계도. UTF-8 JSON.

## 최상위

| 키 | 필수 | 설명 |
|----|:---:|------|
| `meta` | ✅ | 덱 정보 |
| `slides` | ✅ | 슬라이드 배열(순서대로) |
| `derived` | | 계산값 선언 `[{"value": "23%", "formula": "(4520-3675)/3675", "inputs": ["S01: 4,520만", "S01: 3,675만"]}]` |
| `given` | | 사용자가 대화에서 준 값 `["목표 5,000만 원"]` |

## meta

| 키 | 설명 |
|----|------|
| `title`, `subtitle` | 표지 제목·부제 |
| `audience`, `purpose` | 보고 대상·목적(기록용) |
| `date`, `author` | 표지 하단 표시. date 생략 시 오늘 |
| `logo` | 표지에 넣을 이미지 파일 경로 |
| `template` | 회사 템플릿 .pptx 경로(`--template`가 우선) |
| `font_family` | 글꼴 이름. 생략 시 템플릿 글꼴 → "맑은 고딕" |
| `accent` | 강조색 `#RRGGBB` |

## 슬라이드 공통 키

| 키 | 설명 |
|----|------|
| `type` | 아래 9종 중 하나 |
| `headline` | 한 문장 메시지(title·agenda·closing 외 필수) |
| `takeaway` | 하단 강조 상자 한 줄(선택) |
| `sources` | 출처 `["S01 p.3", "S04"]` — 하단에 파일명으로 표시, 노트에도 기록 |
| `notes` | 발표자 노트 |

## 유형별 키

| type | 키 | 비고 |
|------|----|------|
| `title` | `title`, `subtitle` (생략 시 meta 값) | |
| `agenda` | `items: [str]` | headline 생략 시 "목차" |
| `section` | `headline`, `subtitle` | 10장 이상일 때만 |
| `bullets` | `bullets: [str \| {"text", "level": 0~2}]` | 상위 6개 이하 |
| `kpi` | `kpis: [{"label", "value", "delta", "note"}]` | 2~4개. delta가 +/▲면 녹색, -/▼면 빨강 |
| `chart` | `chart: {"kind", "categories", "series": [{"name", "values"}], "unit", "number_format", "title"}` | kind: column, bar, line, pie, doughnut, stacked_column, stacked_bar. values는 숫자(문자열 금지) |
| `table` | `table: {"columns": [str], "rows": [[...]]}` | 12행 이하. 숫자 셀은 자동 오른쪽 정렬 |
| `two_column` | `left`, `right`: `{"title", "bullets"}` | 비교·장단점 |
| `closing` | `headline`, `bullets`, `contact` | 다음 단계·요청 |

## 예시(축약)

```json
{
  "meta": {"title": "주간 외환시장 전망", "subtitle": "무역회사 관점 요약", "audience": "과장", "author": "재무팀"},
  "derived": [],
  "given": [],
  "slides": [
    {"type": "title"},
    {"type": "kpi", "headline": "이번 주 달러/원은 1,440~1,470원 범위가 예상된다",
     "kpis": [{"label": "예상 범위", "value": "1,440~1,470원"}, {"label": "전주 종가", "value": "1,452.3원"}],
     "takeaway": "상단 돌파 시 수입 결제 비용이 늘어난다", "sources": ["S01 p.1"]},
    {"type": "chart", "headline": "최근 4주 환율은 상승 흐름이다",
     "chart": {"kind": "line", "categories": ["2/23", "3/2", "3/9", "3/16"],
               "series": [{"name": "달러/원", "values": [1431.2, 1438.5, 1447.0, 1452.3]}], "unit": "원"},
     "sources": ["S01 p.2"]},
    {"type": "closing", "headline": "대응 방안", "bullets": ["결제 대금 분할 환전 검토"]}
  ]
}
```

위 숫자는 형식 예시일 뿐이다. 실제 outline의 숫자는 반드시 sources에서 가져온다.

## 자주 나는 오류

| build_deck 메시지 | 원인 |
|-------------------|------|
| `headline이 없습니다` | 내용 슬라이드에 headline 누락 |
| `값 개수가 categories와 다름` | 차트 series 값 길이 불일치 |
| `열 개수가 columns와 다름` | 표 행의 칸 수 불일치 |
| `지원하지 않는 차트 종류` | kind 오타 |
