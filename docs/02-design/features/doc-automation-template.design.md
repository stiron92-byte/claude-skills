# Design: 회사 PPT 템플릿 지원 (doc-automation-template)

> Plan: `docs/01-plan/features/doc-automation-template.plan.md`

## 1. 아키텍처 개요

### 전체 데이터 흐름

```
[사용자 입력]
    │
    ├── --input data.csv          (기존)
    ├── --template company.pptx   (개선)
    └── --output output/          (기존)
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  generate_report.py (오케스트레이터)                        │
│                                                          │
│  Step 0 (신규): 템플릿 분석                                │
│  ┌────────────────────┐    ┌────────────────────┐        │
│  │ template_analyzer   │───▶│ StyleConfig        │        │
│  │ (template_analyzer  │    │ (style_config.py)  │        │
│  │  .py)               │    │                    │        │
│  │ - 레이아웃 목록      │    │ - colors {}        │        │
│  │ - 플레이스홀더 맵    │    │ - fonts {}         │        │
│  │ - 테마 색상          │    │ - slide_size {}    │        │
│  │ - 슬라이드 크기      │    │ - layouts []       │        │
│  └────────────────────┘    └────────┬───────────┘        │
│                                     │                     │
│  Step 1 (기존): 데이터 분석          │                     │
│  ┌────────────────────┐             │                     │
│  │ analyze_data.py    │             │                     │
│  │ → analysis dict    │             │                     │
│  └────────┬───────────┘             │                     │
│           │                         │                     │
│  Step 2 (개선): PPT 생성            │                     │
│  ┌────────▼─────────────────────────▼──────────┐         │
│  │ create_pptx.py                               │         │
│  │ - StyleConfig 기반 색상/폰트                   │         │
│  │ - 플레이스홀더 우선, fallback으로 절대좌표       │         │
│  │ - 슬라이드 크기 비율 계산                       │         │
│  └─────────────────────────────────────────────┘         │
│                                                          │
│  Step 3 (기존): 이메일 생성 (변경 없음)                     │
└──────────────────────────────────────────────────────────┘
```

### 모듈 의존 관계

```
template_analyzer.py ──▶ style_config.py
                              │
                              ▼
generate_report.py ──▶ create_pptx.py (StyleConfig 수신)
       │
       ▼
  analyze_data.py (변경 없음)
  generate_email.py (변경 없음)
```

## 2. 모듈별 상세 설계

---

### 2.1 `scripts/style_config.py` (신규)

색상, 폰트, 슬라이드 크기, 레이아웃 정보를 하나의 객체로 관리한다.

#### 클래스: `StyleConfig`

```python
from dataclasses import dataclass, field
from pptx.dml.color import RGBColor


@dataclass
class StyleConfig:
    """PPT 스타일 설정. 템플릿에서 추출하거나 기본값을 사용."""

    # ── 색상 (역할 기반) ──
    colors: dict = field(default_factory=lambda: {
        "background":  "#F8F9FA",
        "title_text":  "#2C3E50",
        "body_text":   "#2C2C2C",
        "accent":      "#4A90D9",
        "accent_dark": "#2C3E50",
        "border":      "#DEE2E6",
        "card_fill":   "#FFFFFF",
        "success":     "#50C878",
        "warning":     "#E85D75",
        "muted":       "#6C757D",
    })

    # ── 폰트 3계층 ──
    fonts: dict = field(default_factory=lambda: {
        "display":  {"size_pt": 44, "bold": True},
        "heading":  {"size_pt": 28, "bold": True},
        "subhead":  {"size_pt": 20, "bold": True},
        "body":     {"size_pt": 14, "bold": False},
        "caption":  {"size_pt": 11, "bold": False},
        "small":    {"size_pt": 10, "bold": False},
    })
    font_family: str | None = None  # None이면 python-pptx 기본값

    # ── 슬라이드 크기 ──
    slide_width: float = 13.333   # inches
    slide_height: float = 7.5     # inches

    # ── 레이아웃 매핑 (템플릿 분석 후 채워짐) ──
    layouts: dict = field(default_factory=dict)
    # 예: {"cover": 0, "content": 1, "blank": 6, ...}

    # ── 헬퍼 메서드 ──
    def rgb(self, role: str) -> RGBColor:
        """색상 역할명 → RGBColor 변환."""
        hex_str = self.colors.get(role, "#000000").lstrip("#")
        return RGBColor(int(hex_str[:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

    def font(self, level: str) -> dict:
        """폰트 레벨명 → {size_pt, bold} 반환."""
        return self.fonts.get(level, self.fonts["body"])

    def x(self, ratio: float) -> float:
        """수평 비율(0.0~1.0) → 인치 변환."""
        return self.slide_width * ratio

    def y(self, ratio: float) -> float:
        """수직 비율(0.0~1.0) → 인치 변환."""
        return self.slide_height * ratio
```

#### 팩토리 함수

```python
def default_style() -> StyleConfig:
    """템플릿 없을 때 기존과 동일한 기본 스타일."""
    return StyleConfig()


def from_template_info(info: dict) -> StyleConfig:
    """template_analyzer의 분석 결과 dict → StyleConfig 변환."""
    style = StyleConfig()

    if info.get("colors"):
        style.colors.update(info["colors"])
    if info.get("font_family"):
        style.font_family = info["font_family"]
    if info.get("slide_width"):
        style.slide_width = info["slide_width"]
        style.slide_height = info["slide_height"]
    if info.get("layouts"):
        style.layouts = info["layouts"]

    return style
```

---

### 2.2 `scripts/template_analyzer.py` (신규)

회사 PPT 템플릿을 열어 레이아웃, 플레이스홀더, 테마 색상, 슬라이드 크기를 추출한다.

#### 메인 함수: `analyze_template()`

```python
def analyze_template(template_path: str) -> dict:
    """템플릿 파일을 분석하여 TemplateInfo dict를 반환.

    Returns:
        {
            "slide_width": float,     # inches
            "slide_height": float,
            "colors": {               # 테마 색상 (역할 매핑)
                "accent": "#XXXXXX",
                "title_text": "#XXXXXX",
                ...
            },
            "font_family": str | None,
            "layouts": {              # 레이아웃 인덱스 매핑
                "cover": 0,
                "title_content": 1,
                "blank": 6,
                ...
            },
            "placeholders": {         # 레이아웃별 플레이스홀더
                0: [
                    {"idx": 0, "type": "TITLE", "left": ..., "top": ..., "width": ..., "height": ...},
                    {"idx": 1, "type": "SUBTITLE", ...},
                ],
                1: [
                    {"idx": 0, "type": "TITLE", ...},
                    {"idx": 1, "type": "BODY", ...},
                ],
                ...
            },
            "existing_slide_count": int,  # 제거해야 할 기존 슬라이드 수
        }
    """
```

#### 내부 함수

| 함수 | 역할 | 반환 |
|------|------|------|
| `_extract_slide_size(prs)` | `prs.slide_width/height`를 인치로 변환 | `(width_inches, height_inches)` |
| `_extract_theme_colors(prs)` | slide_master XML에서 `a:clrScheme` 파싱 | `dict` (dk1, lt1, accent1~6 등 → 역할 매핑) |
| `_extract_font_family(prs)` | 테마의 major/minor 폰트 추출 | `str \| None` |
| `_analyze_layouts(prs)` | 모든 slide_layout 순회, 이름/플레이스홀더 추출 | `(layouts_map, placeholders_map)` |
| `_classify_layout(layout)` | 레이아웃의 용도를 추론 (cover, content, blank 등) | `str` |

#### 테마 색상 → 역할 매핑 규칙

```python
THEME_TO_ROLE = {
    "dk1":     "title_text",    # Dark 1 → 제목 텍스트
    "dk2":     "body_text",     # Dark 2 → 본문 텍스트
    "lt1":     "card_fill",     # Light 1 → 카드 배경
    "lt2":     "background",    # Light 2 → 슬라이드 배경
    "accent1": "accent",        # Accent 1 → 주요 강조색
    "accent2": "warning",       # Accent 2 → 경고/빨강 계열
    "accent3": "success",       # Accent 3 → 성공/초록 계열
    "accent4": "accent_dark",   # Accent 4 → 보조 강조색
    "accent5": "border",        # Accent 5 → 테두리
    "accent6": "muted",         # Accent 6 → 회색/보조
}
```

#### 레이아웃 분류 규칙

| 판별 조건 | 분류 |
|----------|------|
| 이름에 "Title Slide", "표지" 포함 또는 TITLE+SUBTITLE만 있음 | `cover` |
| 이름에 "Title and Content", "제목+내용" 포함 또는 TITLE+BODY | `title_content` |
| 이름에 "Two Content", "2단" 포함 | `two_content` |
| 이름에 "Blank", "빈" 포함 또는 플레이스홀더 0개 | `blank` |
| 이름에 "Section", "구분" 포함 | `section` |
| 그 외 | `other` |

---

### 2.3 `scripts/create_pptx.py` (리팩토링)

#### 변경 요약

| 항목 | Before | After |
|------|--------|-------|
| 함수 시그니처 | `create_xxx_slide(prs, analysis)` | `create_xxx_slide(prs, analysis, style: StyleConfig)` |
| 색상 | 모듈 상수 `BRAND_PRIMARY` 등 | `style.rgb("accent")` 등 |
| 폰트 크기 | 매직 넘버 `font_size=44` | `style.font("display")["size_pt"]` |
| 좌표 | `Inches(1.5)` 절대값 | `Inches(style.x(0.112))` 비율값 |
| 슬라이드 추가 | `prs.slide_layouts[6]` 고정 | `prs.slide_layouts[style.layouts.get("blank", 6)]` |
| 플레이스홀더 | 미사용 | 있으면 우선 사용, 없으면 텍스트박스 fallback |

#### `create_presentation()` 변경

```python
def create_presentation(
    analysis: dict,
    output_path: str,
    template_path: str = None,
    style: StyleConfig = None,
) -> str:
    """분석 결과를 기반으로 PPT를 생성합니다.

    Args:
        analysis: analyze_data의 분석 결과
        output_path: 출력 파일 경로
        template_path: 회사 PPT 템플릿 경로 (선택)
        style: StyleConfig (None이면 기본 스타일 사용)
    """
    if style is None:
        style = default_style()

    if template_path and Path(template_path).exists():
        prs = Presentation(template_path)
        # 기존 샘플 슬라이드 제거
        _remove_existing_slides(prs)
    else:
        prs = Presentation()
        prs.slide_width = Inches(style.slide_width)
        prs.slide_height = Inches(style.slide_height)

    create_cover_slide(prs, analysis, style)
    create_summary_slide(prs, analysis, style)
    create_chart_slide(prs, analysis, style)
    create_issues_slide(prs, analysis, style)
    create_plan_slide(prs, analysis, style)

    prs.save(output_path)
    return output_path
```

#### 슬라이드 생성 함수 변경 패턴

**Before** (표지 예시):
```python
def create_cover_slide(prs, analysis):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # always blank
    _add_bg_shape(slide, BRAND_PRIMARY)                  # hardcoded color
    _add_text_box(slide, 1.5, 1.5, 10, 1.2,            # hardcoded position
                  "주간 업무 보고서", font_size=44, ...)  # hardcoded size
```

**After**:
```python
def create_cover_slide(prs, analysis, style: StyleConfig):
    layout_idx = style.layouts.get("cover", style.layouts.get("blank", 6))
    slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])

    # 플레이스홀더 시도
    title_ph = _find_placeholder(slide, "TITLE")
    if title_ph:
        title_ph.text = "주간 업무 보고서"
        _apply_font(title_ph, style, "display", "card_fill")
    else:
        # fallback: 기존 방식 (비율 좌표)
        _add_bg_shape(slide, style.rgb("accent"))
        _add_text_box(slide, style.x(0.112), style.y(0.2), style.x(0.75), style.y(0.16),
                      "주간 업무 보고서",
                      font_size=style.font("display")["size_pt"],
                      bold=True, color=style.rgb("card_fill"),
                      alignment=PP_ALIGN.CENTER)
```

#### 신규 헬퍼 함수

```python
def _find_placeholder(slide, ph_type: str):
    """슬라이드에서 특정 타입의 플레이스홀더를 찾는다.
    ph_type: "TITLE", "BODY", "SUBTITLE", "PICTURE" 등
    없으면 None 반환.
    """

def _apply_font(placeholder, style: StyleConfig, level: str, color_role: str):
    """플레이스홀더에 StyleConfig 기반 폰트를 적용."""

def _remove_existing_slides(prs):
    """템플릿의 기존 슬라이드를 모두 제거. (마스터/레이아웃은 유지)"""
```

---

### 2.4 `scripts/generate_report.py` (수정)

Step 0 (템플릿 분석)을 추가한다.

```python
def main():
    # ... argparse ...

    # Step 0: 템플릿 분석 (신규)
    style = default_style()
    if args.template:
        print("\n[STEP 0] 템플릿 분석")
        print("-" * 40)
        from template_analyzer import analyze_template
        from style_config import from_template_info
        info = analyze_template(args.template)
        style = from_template_info(info)
        print(f"  슬라이드 크기: {style.slide_width}x{style.slide_height} 인치")
        print(f"  레이아웃 {len(style.layouts)}개 감지")
        print(f"  테마 색상: {style.colors.get('accent', 'default')}")

    # Step 1: 데이터 분석 (기존과 동일)
    # ...

    # Step 2: PPT 생성 (style 전달)
    create_presentation(analysis, pptx_path, args.template, style)

    # Step 3: 이메일 생성 (변경 없음)
    # ...
```

---

## 3. 인터페이스 정의

### 모듈 간 데이터 흐름

```
template_analyzer.analyze_template(path: str)
    → dict (TemplateInfo)
        → style_config.from_template_info(info: dict)
            → StyleConfig
                → create_pptx.create_presentation(analysis, output, template, style)
```

### TemplateInfo 스키마

```python
TemplateInfo = {
    "slide_width": float,           # inches
    "slide_height": float,          # inches
    "colors": {                     # 역할 → hex
        "accent": str,
        "title_text": str,
        "body_text": str,
        "background": str,
        "card_fill": str,
        "border": str,
        "success": str,
        "warning": str,
        "muted": str,
    },
    "font_family": str | None,
    "layouts": {                    # 용도 → 레이아웃 인덱스
        "cover": int,
        "title_content": int,
        "two_content": int,
        "blank": int,
        "section": int,
    },
    "placeholders": {               # 레이아웃 인덱스 → 플레이스홀더 목록
        int: [
            {
                "idx": int,
                "type": str,        # "TITLE", "BODY", "SUBTITLE", "PICTURE"
                "left": float,      # inches
                "top": float,
                "width": float,
                "height": float,
            }
        ]
    },
    "existing_slide_count": int,
}
```

## 4. 슬라이드별 렌더링 전략

| 슬라이드 | 우선 레이아웃 | fallback | 플레이스홀더 사용 |
|----------|-------------|----------|----------------|
| 표지 | `cover` | `blank` | TITLE → 보고서 제목, SUBTITLE → 기간 |
| KPI 요약 | `title_content` | `blank` | TITLE → "핵심 지표 요약", BODY 미사용 (KPI 카드는 도형으로 그림) |
| 상세 차트 | `title_content` | `blank` | TITLE → "상세 분석", BODY 미사용 (차트 이미지 삽입) |
| 이슈/액션 | `two_content` | `blank` | TITLE → "주요 이슈 & 액션 아이템" |
| 다음주 계획 | `title_content` | `blank` | TITLE → "다음 주 계획" |

**핵심 원칙**: 플레이스홀더가 있으면 사용, 없으면 기존 절대좌표 방식으로 fallback (비율 좌표 적용)

## 5. 좌표 비율 변환표

기존 하드코딩 좌표를 16:9 기준 비율로 변환:

| 기존 (인치) | 비율 (x/width, y/height) | 용도 |
|------------|-------------------------|------|
| x=0.5 | 0.0375 | 좌측 마진 |
| x=0.8 | 0.06 | 콘텐츠 시작 |
| x=1.5 | 0.112 | 제목 시작 |
| y=0.15 | 0.02 | 헤더바 텍스트 |
| y=1.3 | 0.173 | 헤더 아래 콘텐츠 시작 |
| y=1.5 | 0.2 | 표지 제목 위치 |
| width=13.333 | 1.0 | 전체 폭 |
| height=1.0 | 0.133 | 헤더 바 높이 |

## 6. 구현 순서

| 순서 | 작업 | 파일 | 의존 |
|------|------|------|------|
| 1 | StyleConfig 클래스 구현 | `style_config.py` | 없음 |
| 2 | 템플릿 분석기 구현 | `template_analyzer.py` | style_config.py |
| 3 | create_pptx.py 리팩토링 | `create_pptx.py` | style_config.py |
| 4 | generate_report.py 연결 | `generate_report.py` | 1, 2, 3 |
| 5 | 샘플 템플릿 생성 + 테스트 | `samples/` | 4 |

## 7. 하위 호환성 보장

- `--template` 미지정 시: `default_style()` 사용 → 기존과 동일한 색상/크기/좌표로 동작
- `create_presentation()` 기존 시그니처 유지: `style=None`이면 내부에서 default 생성
- 기존 `create_brand_template.py`는 그대로 동작 (별도 리팩토링은 후순위)
