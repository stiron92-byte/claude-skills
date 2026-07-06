#!/usr/bin/env python3
"""PPT 스타일 설정 모듈.

색상, 폰트, 슬라이드 크기, 레이아웃 정보를 하나의 객체로 관리합니다.
템플릿에서 추출하거나 기본값을 사용합니다.

참고: 역할 기반 색상 시스템과 폰트 3계층 체계는
pptx-design-styles (https://github.com/corazzon/pptx-design-styles) 패턴을 차용.
"""

from dataclasses import dataclass, field

from pptx.dml.color import RGBColor
from pptx.util import Inches


# ──────────────────────────────────────────────
# 기본 색상/폰트 상수
# ──────────────────────────────────────────────
DEFAULT_COLORS = {
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
}

DEFAULT_FONTS = {
    "display":  {"size_pt": 44, "bold": True},
    "heading":  {"size_pt": 28, "bold": True},
    "subhead":  {"size_pt": 20, "bold": True},
    "body":     {"size_pt": 14, "bold": False},
    "caption":  {"size_pt": 11, "bold": False},
    "small":    {"size_pt": 10, "bold": False},
}


# ──────────────────────────────────────────────
# StyleConfig
# ──────────────────────────────────────────────
@dataclass
class StyleConfig:
    """PPT 스타일 설정. 템플릿에서 추출하거나 기본값을 사용."""

    colors: dict = field(default_factory=lambda: dict(DEFAULT_COLORS))
    fonts: dict = field(default_factory=lambda: dict(DEFAULT_FONTS))
    font_family: str | None = None
    slide_width: float = 13.333
    slide_height: float = 7.5
    layouts: dict = field(default_factory=dict)

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

    def get_layout_index(self, purpose: str, fallback: int = 6) -> int:
        """레이아웃 용도명 → 인덱스. 없으면 fallback 반환."""
        return self.layouts.get(purpose, fallback)


# ──────────────────────────────────────────────
# 팩토리 함수
# ──────────────────────────────────────────────
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
    if info.get("slide_height"):
        style.slide_height = info["slide_height"]
    if info.get("layouts"):
        style.layouts = info["layouts"]

    return style
