---
name: excel-automation
description: "엑셀 파일을 전달받아 데이터 정리, 분석/시각화, 멀티탭 취합을 자동 수행하는 스킬. 사용자가 '정리해줘', '분석해줘', '취합해줘', '엑셀 자동화', '데이터 클리닝', '중복 제거', '차트 만들어줘', '탭 합쳐줘', '시트 합치기', '엑셀 데이터 분석', '매출 분석', '통계 내줘', '이상값 찾아줘', '전화번호 정리', '날짜 형식 통일', '엑셀 요약', '시각화해줘' 등의 요청을 하면 이 스킬을 사용하세요. 엑셀 파일(.xlsx, .csv)이 첨부되어 있고 단순 셀 편집이 아닌 데이터 가공/분석/병합 작업이 필요한 경우에도 반드시 트리거하세요. xlsx 스킬과 다른 점: 이 스킬은 데이터 품질 개선, 통계 분석, 멀티시트 병합이라는 고수준 자동화 워크플로를 제공합니다."
---

# Excel Automation Skill

사용자가 엑셀 파일을 전달하면 세 가지 핵심 기능 중 적절한 것을 판단하여 실행한다.

## 기능 판단 기준

사용자의 자연어 요청에서 의도를 파악한다.

- **"정리해줘", "클리닝", "중복 제거", "형식 통일", "오류 수정"** → 기능 1: 데이터 정리
- **"분석해줘", "통계", "차트", "시각화", "인사이트", "비교"** → 기능 2: 분석과 시각화
- **"취합해줘", "합쳐줘", "시트 합치기", "탭 병합", "통합"** → 기능 3: 멀티탭 취합
- 의도가 불명확할 경우 → 사용자에게 물어본다

복합 요청("정리하고 분석까지 해줘")이면 해당 기능들을 순차적으로 실행한다.

## 공통 사항

### 파일 읽기
```python
import pandas as pd

# 단일 시트
df = pd.read_excel('input.xlsx')

# 전체 시트 구조 파악
all_sheets = pd.read_excel('input.xlsx', sheet_name=None)
for name, sheet_df in all_sheets.items():
    print(f"[{name}] {sheet_df.shape[0]}행 x {sheet_df.shape[1]}열")
    print(f"  컬럼: {list(sheet_df.columns)}")
```

### 결과 저장
결과물은 항상 새 엑셀 파일(.xlsx)로 저장한다. 원본 파일은 절대 덮어쓰지 않는다.
파일명 규칙: `{원본파일명}_{작업종류}_{날짜}.xlsx` (예: `매출데이터_정리완료_20260401.xlsx`)

### xlsx 스킬 활용
엑셀 파일을 생성하거나 저장할 때는 xlsx 스킬의 가이드라인을 따른다. 특히 수식 사용 시 openpyxl로 작성한 뒤 반드시 `scripts/recalc.py`로 재계산한다.

---

## 기능 1: 데이터 정리

목표: 엑셀 데이터의 품질 문제를 자동으로 탐지하고, 수정하고, 변경 내역을 투명하게 보고한다.

### 실행 순서

#### Step 1: 현황 파악
데이터를 읽고 전체 구조를 먼저 이해한다.

```python
df = pd.read_excel('input.xlsx')
print(f"총 {len(df)}행, {len(df.columns)}열")
print(f"컬럼: {list(df.columns)}")
print(df.dtypes)
print(df.isnull().sum())  # 컬럼별 빈 셀 수
```

#### Step 2: 중복 행 탐지 및 제거

**완전 일치 중복**: 모든 컬럼이 동일한 행을 제거한다.

```python
exact_dupes = df[df.duplicated(keep=False)]
df_clean = df.drop_duplicates(keep='first')
```

**유사 중복 (핵심 컬럼 기준)**: 이름, 전화번호, 이메일 등 핵심 식별 컬럼을 기준으로 유사한 행을 찾는다. 어떤 컬럼을 핵심 컬럼으로 볼지는 데이터 구조를 보고 판단한다. 예를 들어 이름+전화번호가 같으면서 다른 값이 다른 경우, 이를 유사 중복 후보로 표시한다.

```python
# 핵심 컬럼 예시 (데이터에 맞게 조정)
key_cols = ['이름', '전화번호']  # 또는 ['상품코드'], ['이메일'] 등
near_dupes = df[df.duplicated(subset=key_cols, keep=False)]
```

유사 중복은 자동 삭제하지 않고, 별도 시트에 후보 목록을 제시하여 사용자가 판단할 수 있게 한다.

#### Step 3: 형식 통일

**전화번호**: 숫자만 추출한 뒤 010-XXXX-XXXX 형태로 변환한다.

```python
import re

def normalize_phone(val):
    if pd.isna(val):
        return val
    digits = re.sub(r'\D', '', str(val))
    if len(digits) == 11 and digits.startswith('010'):
        return f'{digits[:3]}-{digits[3:7]}-{digits[7:]}'
    elif len(digits) == 10 and digits.startswith('01'):
        return f'{digits[:3]}-{digits[3:6]}-{digits[6:]}'
    return str(val)  # 변환 불가 시 원본 유지
```

**비정상 번호 처리 원칙**: 자릿수가 맞지 않거나(예: 010-777-888), 영문이 섞여 있거나(예: 010-7788-99OO), 기타 정상적인 전화번호로 볼 수 없는 값은 **절대 임의로 수정하거나 추측하여 채우지 않는다.** 원본 값을 그대로 유지하고, "오타_이상값_후보" 시트에 해당 행과 사유를 기록한다. 이런 데이터는 잘못 수정하면 더 큰 문제를 일으킬 수 있기 때문에 사람이 직접 원본을 확인하고 판단해야 한다.

**날짜**: 다양한 형식을 YYYY-MM-DD로 통일한다.

```python
def normalize_date(val):
    if pd.isna(val):
        return val
    try:
        return pd.to_datetime(val).strftime('%Y-%m-%d')
    except:
        return str(val)  # 파싱 불가 시 원본 유지
```

형식 변환이 불가능한 값은 원본을 유지하되, "오타_이상값_후보" 시트에 해당 항목과 사유를 기록한다. 변경 리포트에도 "변환 실패 N건"으로 집계한다.

#### Step 4: 빈 셀 탐지 및 처리

빈 셀을 자동으로 채우지 않는다. 대신 빈 셀 현황을 정리하여 사용자에게 보고한다.

```python
null_report = df.isnull().sum()
null_report = null_report[null_report > 0]
```

보고 내용: 컬럼별 빈 셀 수, 전체 대비 비율, 추천 처리 방법(삭제, 기본값 채우기, 무시 등). 사용자가 처리 방법을 선택하면 그에 맞게 적용한다.

#### Step 5: 오타/이상값 탐지

**이메일 도메인**: 흔한 도메인의 오타를 탐지한다 (gamil.com → gmail.com, naver.con → naver.com 등).

```python
common_domains = ['gmail.com', 'naver.com', 'daum.net', 'hanmail.net', 'kakao.com', 'yahoo.com', 'hotmail.com']

def check_email_typo(email):
    if pd.isna(email) or '@' not in str(email):
        return None
    domain = str(email).split('@')[-1].lower()
    # 편집 거리 1~2인 유사 도메인 탐지
    for correct in common_domains:
        if domain != correct and levenshtein_distance(domain, correct) <= 2:
            return f'{domain} → {correct}?'
    return None
```

**카테고리/범주형 값**: 유사하지만 다른 값들을 탐지한다 ("서울시" vs "서울특별시", "전자제품" vs "전자 제품").

**숫자 이상값**: 해당 컬럼의 통계(평균, 표준편차)를 기준으로 극단적인 값을 표시한다.

오타와 이상값도 자동 수정하지 않는다. 의심 목록을 별도 시트("오타_이상값_후보")에 정리하여 사용자가 확인할 수 있게 한다.

#### Step 6: 변경 리포트 생성

정리 전후의 변경 사항을 "변경리포트" 시트에 기록한다.

| 항목 | 내용 |
|------|------|
| 완전 일치 중복 제거 | N건 |
| 유사 중복 후보 | N건 (별도 시트 참고) |
| 전화번호 형식 수정 | N건 |
| 날짜 형식 수정 | N건 |
| 빈 셀 발견 | N건 (컬럼별 상세) |
| 오타/이상값 후보 | N건 (별도 시트 참고) |

각 항목에는 구체적인 수정 내역(어떤 셀의 값이 뭐에서 뭐로 바뀌었는지)을 포함한다.

#### 최종 출력 파일 구성
- **시트 1 "정리완료"**: 정리된 데이터
- **시트 2 "변경리포트"**: 변경 사항 요약 + 상세 내역
- **시트 3 "유사중복_후보"**: 유사 중복 의심 행 (있는 경우)
- **시트 4 "오타_이상값_후보"**: 오타/이상값 의심 항목 (있는 경우)

---

## 기능 2: 분석과 시각화

목표: 데이터를 분석하고, 핵심 인사이트를 도출하며, 적절한 차트를 생성한다.

### 실행 순서

#### Step 1: 데이터 파악 및 요약 통계

```python
df = pd.read_excel('input.xlsx')

# 수치형 컬럼 요약 통계
summary = df.describe()

# 날짜 컬럼이 있으면 기간 파악
date_cols = df.select_dtypes(include=['datetime64']).columns
```

수치형 컬럼별 합계, 평균, 최대/최소, 중앙값을 산출한다. 날짜 컬럼이 있으면 시간 흐름에 따른 추이도 파악한다.

#### Step 2: 사용자 질문 기반 분석

사용자가 구체적인 질문을 했으면("지난달 대비 매출 변화", "카테고리별 비교") 해당 분석을 수행한다. 질문이 없으면 데이터 구조를 보고 의미 있는 분석을 자동으로 선택한다.

자동 분석 선택 기준:
- 날짜 + 수치 컬럼 → 시계열 추이 분석
- 카테고리 + 수치 컬럼 → 그룹별 비교
- 여러 수치 컬럼 → 상관관계 분석
- 지역/카테고리 → 분포 분석

#### Step 3: 차트 생성

데이터 특성에 맞는 차트를 자동으로 선택한다.

**차트 유형 선택 기준:**
- 시계열 추이 → 꺾은선 차트 (Line)
- 카테고리별 비교 → 막대 차트 (Bar)
- 구성비 → 파이 차트 (Pie) - 항목이 7개 이하일 때
- 분포 → 히스토그램 또는 박스플롯
- 2차원 비교 → 히트맵
- 두 수치 변수 관계 → 산점도 (Scatter)

**차트 생성 방식:**
- 간단한 차트(막대, 꺾은선, 파이)는 openpyxl의 내장 차트 기능으로 엑셀 파일 안에 직접 생성한다. 엑셀 내장 차트는 사용자가 나중에 직접 수정할 수 있어서 편리하다.
- 복잡한 차트(히트맵, 다축 차트, 커스텀 시각화)는 matplotlib로 이미지를 생성한 뒤 엑셀에 삽입한다.

```python
# openpyxl 내장 차트 예시
from openpyxl.chart import BarChart, Reference

chart = BarChart()
chart.title = "카테고리별 매출"
chart.y_axis.title = "매출(원)"
data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row, max_col=2)
cats = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
ws_chart.add_chart(chart, "A1")
```

```python
# matplotlib 이미지 차트 예시
import matplotlib.pyplot as plt
from openpyxl.drawing.image import Image

plt.rcParams['font.family'] = 'DejaVu Sans'  # 한글 폰트는 환경에 따라 조정
fig, ax = plt.subplots(figsize=(10, 6))
# ... 차트 그리기 ...
fig.savefig('chart.png', dpi=150, bbox_inches='tight')
plt.close()

ws.add_image(Image('chart.png'), 'A1')
```

한글 폰트가 깨질 수 있으므로, matplotlib 사용 시 시스템에 설치된 한글 폰트를 확인하고 설정한다.

#### Step 4: 핵심 인사이트 도출

분석 결과에서 주목할 만한 패턴 3~5개를 도출한다. **인사이트는 반드시 한글로 작성한다.** 영어로 작성하지 않는다.

각 인사이트는 한 줄 요약이 아니라 **줄글 형태로 상세하게 설명**한다. 단순히 숫자만 나열하는 것이 아니라, 그 수치가 왜 중요한지, 어떤 맥락에서 해석할 수 있는지, 비즈니스적으로 어떤 의미가 있는지를 2~4문장으로 풀어서 작성한다.

좋은 예:
"3월 매출은 전월 대비 23% 증가한 4,520만 원을 기록했습니다. 이 증가세는 주로 '전자제품' 카테고리가 주도했으며, 전체 증가분의 67%를 차지했습니다. 특히 무선 이어폰 Pro 단일 상품이 전자제품 카테고리 매출의 40%를 점유하고 있어, 해당 상품의 재고 관리와 마케팅 투자를 강화하면 추가 성장 여력이 있을 것으로 보입니다."

나쁜 예:
"March sales increased by 23%. Electronics category led the growth."
→ 영어로 작성됨, 한 줄 요약에 불과, 맥락 설명 없음

#### Step 5: 결과 저장

분석 결과를 새 시트 또는 새 파일에 저장한다.

#### 최종 출력 파일 구성
- **시트 1 "요약통계"**: 수치형 컬럼별 통계 (합계, 평균, 최대, 최소, 중앙값)
- **시트 2 "분석결과"**: 상세 분석 테이블
- **시트 3 "차트"**: 생성된 차트들
- **시트 4 "인사이트"**: 핵심 발견 3~5개를 한글 줄글로 상세 설명

---

## 기능 3: 멀티탭 취합

목표: 여러 시트(탭)에 흩어진 데이터를 하나의 관리 시트로 통합한다.

### 실행 순서

#### Step 1: 전체 시트 구조 파악

```python
all_sheets = pd.read_excel('input.xlsx', sheet_name=None)

for name, df in all_sheets.items():
    print(f"\n=== {name} ===")
    print(f"  행: {len(df)}, 열: {len(df.columns)}")
    print(f"  컬럼: {list(df.columns)}")
    print(f"  샘플:\n{df.head(2)}")
```

각 시트의 컬럼명, 데이터 타입, 행 수를 비교하여 공통점과 차이점을 파악한다.

#### Step 2: 공통 키 식별

시트 간에 데이터를 연결할 수 있는 공통 키를 자동으로 찾는다. 상품코드, ID, 이름 등 고유한 값을 가진 컬럼이 후보이다.

```python
# 각 시트에서 고유값 비율이 높은 컬럼 = 키 후보
for name, df in all_sheets.items():
    for col in df.columns:
        unique_ratio = df[col].nunique() / len(df)
        if unique_ratio > 0.5:  # 고유값 비율이 50% 이상
            print(f"  [{name}] 키 후보: {col} (고유값 {df[col].nunique()}개)")
```

공통 키가 명확하지 않으면 사용자에게 어떤 컬럼을 기준으로 연결할지 확인한다.

#### Step 3: 원본 시트 보존

**원본 파일의 모든 시트를 결과 파일에 반드시 그대로 포함한다.** 이것은 선택사항이 아니라 필수이다. 사용자가 원본 파일의 쿠팡 탭, 스마트스토어 탭 등을 결과 파일에서도 바로 참조할 수 있어야 한다. 원본 시트를 날려버리면 통합관리 시트의 수식이 참조할 데이터도 없어지고, 사용자가 원본을 다시 열어봐야 하는 불편이 생긴다.

```python
from openpyxl import load_workbook

# 원본 파일을 openpyxl로 열어서 모든 시트를 보존한 채로 작업한다
wb = load_workbook('input.xlsx')
```

pandas로 데이터를 분석/가공하되, 최종 파일 저장은 openpyxl로 원본 시트를 유지한 상태에서 통합관리 시트와 취합리포트 시트를 추가하는 방식으로 한다.

#### Step 4: 데이터 연결 및 취합

공통 키를 기준으로 outer join을 수행한다. 일부 시트에만 존재하는 항목도 누락 없이 포함한다.

```python
from functools import reduce
import pandas as pd

dfs = []
for name, df in all_sheets.items():
    # 컬럼명에 시트명 접두사 추가 (키 컬럼 제외)
    renamed = df.rename(columns={
        col: f"{name}_{col}" for col in df.columns if col != key_col
    })
    dfs.append(renamed)

merged = reduce(lambda left, right: pd.merge(left, right, on=key_col, how='outer'), dfs)
```

#### Step 5: 수식 기반 통합관리 시트 구성

통합관리 시트는 **하드코딩된 값이 아니라 엑셀 수식으로 구성**한다. 이렇게 해야 원본 시트의 데이터가 바뀌면 통합관리 시트도 자동으로 반영된다.

**VLOOKUP/참조 수식 활용**: 통합관리 시트에서 각 채널 데이터를 가져올 때, 원본 시트를 직접 참조하는 VLOOKUP 수식을 사용한다.

```python
# 예시: 통합관리 시트에서 쿠팡 탭의 3월판매량을 VLOOKUP으로 가져오기
# A열에 상품코드가 있고, 쿠팡 시트에서 해당 상품코드의 판매량을 참조
ws['D2'] = '=IFERROR(VLOOKUP(A2,쿠팡!B:K,9,FALSE),"")'

# 합계 컬럼도 SUM 수식으로 넣는다
# 예: 채널별 판매량이 D, F, H, J 열에 있다면
ws['L2'] = '=SUM(D2,F2,H2,J2)'
```

**수식 사용 원칙:**
- 채널별 데이터 참조 → VLOOKUP 또는 INDEX/MATCH 수식으로 원본 시트 참조
- 합계/소계 → SUM 수식
- 비율/차이 계산 → 수식으로 처리
- 값이 없을 수 있는 경우 → IFERROR로 감싸서 에러 방지
- Python으로 값을 계산해서 하드코딩하지 않는다

**레이아웃 원칙:**
- 첫 번째 컬럼은 공통 키 (상품코드, ID 등)
- 이후 각 시트(채널/항목)별로 핵심 수치를 나란히 배치
- 합계/차이 컬럼을 수식으로 추가하여 비교를 돕는다

예시 레이아웃:
| 상품코드 | 쿠팡_판매수(VLOOKUP) | 네이버_판매수(VLOOKUP) | 자사몰_판매수(VLOOKUP) | 합계(SUM) |

수식 작성 후 반드시 xlsx 스킬의 `scripts/recalc.py`로 재계산하여 값이 올바르게 나오는지 검증한다.

#### Step 6: 누락 데이터 표시

특정 시트에만 있는 항목은 VLOOKUP 결과가 빈칸이나 에러로 나타난다. IFERROR 수식으로 감싸서 빈칸 또는 "해당없음"으로 표시하고, 취합 리포트에 시트별 데이터 현황을 기록한다.

#### 최종 출력 파일 구성
- **원본 시트들 전부 유지**: 쿠팡, 스마트스토어, 카카오선물하기, 자사몰, 상품마스터, 재고현황 등 원본 파일의 모든 시트를 그대로 포함
- **시트 추가 "통합관리"**: VLOOKUP/SUM 수식으로 구성된 취합 데이터 (비교가 용이한 레이아웃)
- **시트 추가 "취합리포트"**: 시트별 데이터 건수, 공통 키 기준, 누락 항목 현황

---

## 코드 작성 시 주의사항

- Python 코드는 간결하게 작성한다. 불필요한 주석이나 print문을 남발하지 않는다.
- pandas와 openpyxl을 상황에 맞게 조합하여 사용한다. 데이터 가공은 pandas, 서식/차트는 openpyxl이 적합하다.
- 대용량 파일(10만 행 이상)은 청크 단위로 읽어 메모리 문제를 방지한다.
- 한글 컬럼명과 데이터를 올바르게 처리한다 (encoding 주의).
- 에러 발생 시 원본 데이터가 손실되지 않도록 항상 새 파일에 결과를 저장한다.

## 결과 전달

작업 완료 후 사용자에게 다음을 전달한다:
1. 생성된 엑셀 파일 링크
2. 변경/분석 내역 요약 (대화 내에서 텍스트로, 핵심만 간결하게)
3. 추가 작업 제안 (데이터를 보고 더 할 수 있는 것이 있으면)
