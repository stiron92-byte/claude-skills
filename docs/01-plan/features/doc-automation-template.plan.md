# Plan: 회사 PPT 템플릿 지원 (doc-automation-template)

## 1. 배경 및 목적

### 현재 상황
chapter1-doc-automation은 파일(CSV, PDF, Word 등)을 분석하여 PPT 보고서와 요약 이메일을 자동 생성한다. 그러나 PPT 생성 시 **회사 고유의 PPT 템플릿을 제대로 활용하지 못하는 한계**가 있다.

### 현재 코드의 문제점

| 문제 | 위치 | 설명 |
|------|------|------|
| 슬라이드 레이아웃 무시 | `create_pptx.py:100` | 항상 `slide_layouts[6]` (blank)만 사용. 회사 템플릿의 마스터 레이아웃(제목, 콘텐츠 등) 미활용 |
| 색상 하드코딩 | `create_pptx.py:21-28` | `BRAND_PRIMARY` 등이 코드에 고정. 템플릿의 테마 색상을 읽지 않음 |
| 절대 좌표 배치 | `create_pptx.py` 전체 | 13.333x7.5 인치 기준 하드코딩. 4:3 템플릿이면 레이아웃이 깨짐 |
| 플레이스홀더 미사용 | `create_pptx.py` 전체 | 템플릿에 정의된 제목/본문 영역을 무시하고 텍스트박스를 직접 생성 |
| 기존 슬라이드 미삭제 | `create_pptx.py:328-329` | 템플릿을 열면 기존 샘플 슬라이드가 그대로 남아있음 |

### 목적
사용자가 회사에서 쓰는 기존 PPT 템플릿(.pptx)을 제공하면, 그 **레이아웃, 색상, 폰트, 로고 위치를 자동으로 인식**하여 일관된 브랜드 보고서를 생성하도록 개선한다.

## 2. 요구사항

### 필수 요구사항 (Must Have)

| ID | 요구사항 | 설명 |
|----|---------|------|
| R1 | 템플릿 분석기 | 템플릿 파일을 열어 슬라이드 레이아웃, 플레이스홀더, 테마 색상을 자동 추출 |
| R2 | 플레이스홀더 매핑 | 템플릿의 제목/본문/이미지 플레이스홀더에 내용을 삽입 |
| R3 | 슬라이드 크기 대응 | 16:9, 4:3 등 템플릿의 슬라이드 크기에 맞춰 좌표 자동 계산 |
| R4 | 테마 색상 적용 | 템플릿의 테마 색상을 추출하여 차트, KPI 카드 등에 자동 적용 |
| R5 | 기존 슬라이드 정리 | 템플릿의 샘플/더미 슬라이드를 제거한 뒤 새 콘텐츠 삽입 |
| R6 | 하위 호환성 | 템플릿 없이도 기존처럼 기본 스타일로 동작 (기존 기능 유지) |

### 선택 요구사항 (Nice to Have)

| ID | 요구사항 | 설명 |
|----|---------|------|
| N1 | 레이아웃 자동 선택 | 콘텐츠 유형(표지, KPI, 차트 등)에 맞는 레이아웃을 자동 매칭 |
| N2 | 폰트 상속 | 템플릿에 정의된 폰트 패밀리를 그대로 사용 |
| N3 | 템플릿 프리뷰 | 템플릿 분석 결과를 사람이 확인할 수 있는 요약 출력 |

## 3. 범위

### In Scope
- `scripts/create_pptx.py` 리팩토링
- 새 모듈 `scripts/template_analyzer.py` 추가
- 기존 `--template` 옵션의 동작 개선
- 샘플 회사 템플릿 추가 (`samples/`)

### Out of Scope
- 이메일 생성 로직 변경 (영향 없음)
- 데이터 분석 로직 변경 (영향 없음)
- PowerPoint 매크로/VBA 지원
- Google Slides 연동

## 4. 기술 접근 방식

### 핵심 전략: 템플릿 분석 → 매핑 → 렌더링

```
[회사 템플릿.pptx]
       │
       ▼
┌─────────────────────┐
│  template_analyzer   │  ← 신규 모듈
│  - 레이아웃 목록     │
│  - 플레이스홀더 맵   │
│  - 테마 색상 추출    │
│  - 슬라이드 크기     │
└─────────────────────┘
       │
       ▼  TemplateInfo (dict)
┌─────────────────────┐
│  create_pptx.py     │  ← 리팩토링
│  - 레이아웃 매칭     │
│  - 플레이스홀더 삽입  │
│  - 좌표 비율 계산    │
│  - 테마 색상 사용    │
└─────────────────────┘
       │
       ▼
[브랜드 보고서.pptx]
```

### 주요 기술 포인트

1. **플레이스홀더 감지**: `python-pptx`의 `slide_layout.placeholders`를 순회하여 타입(TITLE, BODY, PICTURE 등) 매핑
2. **테마 색상 추출**: `presentation.slide_masters[0].element`에서 `a:clrScheme` 파싱
3. **좌표 비율화**: 절대 좌표 대신 슬라이드 크기 대비 비율(%)로 변환
4. **레이아웃 매칭**: 레이아웃 이름 또는 플레이스홀더 구성을 기반으로 용도 추론

## 5. 참고 자료: pptx-design-styles

> 출처: https://github.com/corazzon/pptx-design-styles

이 레포는 30개의 PPT 디자인 스타일 스펙을 정의한 AI 스킬 레퍼런스다. Python 코드는 없지만, **설계 패턴**을 차용한다.

### 차용 항목

| 패턴 | 현재 코드 | 차용 후 |
|------|----------|--------|
| 역할 기반 색상 시스템 | `BRAND_PRIMARY`, `BRAND_SECONDARY` 등 6개 고정 | background, title_text, body_text, accent, border, card_fill 등 기능별 분류 |
| StyleConfig 스키마 | 색상/폰트가 코드에 하드코딩 | 외부 설정 dict로 분리 (템플릿에서 추출 또는 기본값 사용) |
| 폰트 3단계 체계 | 함수마다 font_size 산발 지정 | Display(36-44pt), Body(12-16pt), Caption(9-11pt) 3계층 |
| 용도별 스타일 추천 | 단일 디자인만 지원 | 보고 유형(임원/팀/외부)에 따른 스타일 프리셋 (Nice to Have) |

### StyleConfig 구조 예시

```python
style_config = {
    "colors": {
        "background": "#F8F9FA",
        "title_text": "#2C3E50",
        "body_text": "#2C2C2C",
        "accent": "#4A90D9",
        "border": "#DEE2E6",
        "card_fill": "#FFFFFF",
        "success": "#50C878",
        "warning": "#E85D75",
    },
    "fonts": {
        "display": {"size_pt": 44, "bold": True},
        "heading": {"size_pt": 28, "bold": True},
        "body": {"size_pt": 14, "bold": False},
        "caption": {"size_pt": 11, "bold": False},
    },
    "slide_size": {"width_inches": 13.333, "height_inches": 7.5},
}
```

## 6. 수정 대상 파일

| 파일 | 작업 | 설명 |
|------|------|------|
| `scripts/template_analyzer.py` | **신규** | 템플릿 분석 모듈 (레이아웃, 플레이스홀더, 테마 색상, 슬라이드 크기 추출) |
| `scripts/style_config.py` | **신규** | StyleConfig 클래스 — 색상/폰트/크기를 외부화 (pptx-design-styles 패턴 차용) |
| `scripts/create_pptx.py` | **수정** | StyleConfig 기반 렌더링 + 플레이스홀더 삽입으로 리팩토링 |
| `scripts/generate_report.py` | **수정** | 템플릿 분석 단계 추가 |
| `scripts/create_brand_template.py` | **수정** | 플레이스홀더 포함 템플릿 생성 |
| `samples/` | **추가** | 4:3, 16:9 샘플 회사 템플릿 |

## 6. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 회사 템플릿마다 구조가 다름 | 플레이스홀더가 없거나 이름이 다를 수 있음 | fallback: 플레이스홀더 없으면 기존 방식(절대좌표)으로 동작 |
| python-pptx의 테마 색상 접근 제한 | 공식 API가 불완전할 수 있음 | lxml로 XML 직접 파싱 |
| 기존 기능 regression | 템플릿 없는 기본 실행이 깨질 수 있음 | 기존 테스트 케이스 유지, 템플릿 없는 경로 보존 |

## 7. 성공 기준

- [ ] 회사 PPT 템플릿을 `--template`으로 전달하면 해당 레이아웃/색상이 적용된 보고서 생성
- [ ] 4:3, 16:9 두 가지 크기의 템플릿 모두 정상 동작
- [ ] 템플릿 없이 실행해도 기존과 동일하게 동작 (하위 호환)
- [ ] 템플릿의 플레이스홀더(제목, 본문)에 내용이 올바르게 삽입됨
