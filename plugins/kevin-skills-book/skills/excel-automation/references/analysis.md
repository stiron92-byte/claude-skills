# 분석(기능 2) — 질문별 분석, 차트, 인사이트

## 1. 질문을 분석으로 옮기기

| 사용자 질문 | 계산 | 시트·차트 |
|-------------|------|-----------|
| "전체 현황 요약" | 행 수, 합계, 평균, 중앙값, 최대·최소, 기간 | 요약통계(표) |
| "추이", "지난달 대비" | 월(주)별 합계, 전월 대비 증감·증감률 | 월별추이 + 꺾은선 |
| "카테고리별 비교" | 항목별 합계·건수·평균·비중 | 세로 막대, 구성비는 원형(항목 6개 이하일 때만) |
| "가장 많이 팔린 것" | 항목별 합계 상위 10 | 가로 막대(이름이 길면 가로) |
| "월별 × 카테고리" | 피벗 | 셀 히트맵(색 단계 서식) |
| "지역별 객단가" | 합계 ÷ 주문 수 | 막대, 표에 분자·분모도 함께 |
| "작년 같은 달 대비" | 같은 월끼리 비교(기간이 13개월 이상일 때만) | 묶은 막대 |

기간이 부족하면(예: 2개월 데이터로 "추세") 계산하지 말고 "기간이 짧아 추세를 말하기 어렵다"고 전달한다.
날짜를 해석하지 못한 행은 제외하고 개수를 요약통계에 적는다(표준 보고서가 자동으로 한다).

## 2. 도구 함수(scripts/analysis_tools.py)

```python
import sys; sys.path.insert(0, "<스킬 폴더>/scripts")
from openpyxl import load_workbook
from analysis_tools import load_table, write_df, add_chart, add_heatmap, write_insights

df = load_table("<원본.xlsx>")                    # 제목 행이 있어도 머리글을 찾아 읽음
wb = load_workbook("<원본.xlsx>")                 # 원본 시트를 보존한 채 시트를 더한다
t = df.groupby("지역").agg(합계=("결제금액", "sum"), 주문수=("주문번호", "count")).reset_index()
t["객단가"] = (t["합계"] / t["주문수"]).round(0).astype(int)
ws = wb.create_sheet("지역별객단가")
last, _ = write_df(ws, t)                          # 머리글 서식·숫자 서식·열 너비
add_chart(ws, "col", "지역별 객단가", cats_col=1, val_cols=[4], anchor="G2", last_row=last, y_title="원")
write_insights(wb, [("객단가 1위는 서울(52,300원)이다.", "지역별객단가!D2")])
wb.save("<W>/<이름>_분석.xlsx")                   # 원본 경로에 저장하지 않는다
```

| 함수 | 하는 일 |
|------|---------|
| `load_table(path, sheet=None)` | 머리글 행 자동 감지 후 DataFrame |
| `write_df(ws, df, start_row=1, start_col=1)` | 표 쓰기, (마지막 행, 마지막 열) 반환 |
| `add_chart(ws, kind, title, cats_col, val_cols, anchor, last_row=…)` | 엑셀 기본 차트. kind: `col`·`bar`·`line`·`pie` |
| `add_heatmap(ws, "B2:E13")` | 색 단계 조건부 서식 |
| `write_insights(wb, [(문장, 근거 셀), …])` | `인사이트` 시트(번호·인사이트·근거) |

## 3. 차트 규칙

- 엑셀 기본 차트만 쓴다. matplotlib 그림은 값을 확인·수정할 수 없고, verify가 차트로 세지 않는다.
- 차트 하나에 메시지 하나. 제목은 "월별 결제금액 추이"처럼 무엇을 보여 주는지 쓴다.
- 원형은 항목 6개 이하일 때만. 그 이상은 막대.
- 축 숫자 서식은 `#,##0`. 금액 단위가 크면 표에 `만원` 열을 따로 만들어 그 열로 그린다.
- 차트는 표 오른쪽(H열 이후)에 두어 표를 가리지 않는다.

## 4. 인사이트 작성 규칙

- 3~5개. 각 문장은 "무엇이 · 얼마나 · 비교 기준"을 담는다. 예: "카테고리 1위는 전자기기로 57,317,200원이며 전체의 65.1%다."
- 문장 속 숫자는 통합 문서 어딘가의 셀 값이어야 한다. 비율·증감처럼 계산한 값은 먼저 시트에 쓰고 그 값을 인용한다.
- 반올림·단위 표기는 허용된다("약 8,810만 원" ↔ 88,097,750). 반올림 자리까지 맞아야 한다.
- 원인은 데이터로 확인된 것만 말한다. 확인할 수 없으면 "원인 확인 필요"로 쓴다.
- 날짜(2025-01, 3월)와 9 이하 정수(순위·개수)는 숫자 대조에서 빠진다.

## 5. verify_excel analysis 검사

| 검사 | 뜻 | 고치는 법 |
|------|----|-----------|
| input-changed | 원본이 바뀌었다(snapshot과 다름) | 원본 복구 후 새 파일로 다시 |
| no-native-chart | 엑셀 기본 차트가 없다 | `add_chart`로 차트 추가 |
| no-insights | 인사이트 시트·문장이 없다 | `write_insights` |
| insight-number-provenance | 인사이트 숫자가 어느 셀에도 없다 | 숫자를 셀 값으로 바꾸거나 계산값을 시트에 먼저 쓴다 |
| formula-error | 수식 오류 셀 | 수식 수정 후 `recalc.py` |
| forbidden-function | XLOOKUP·FILTER 등 | INDEX/MATCH, SUMIFS로 바꾼다 |

경고 `insight-count`(3~5개 아님), `original-sheets-not-included`(결과에 원본 탭이 없음)는 사용자 요청에 맞으면 그대로 둬도 된다.
