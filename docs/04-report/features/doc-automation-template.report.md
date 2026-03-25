# Completion Report: 회사 PPT 템플릿 지원 (doc-automation-template)

> Date: 2026-03-24
> PDCA Status: `[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ (99.3%) → [Report] ✅`

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| Feature | doc-automation-template |
| 목적 | 회사 기존 PPT 템플릿의 레이아웃/색상/폰트를 자동 인식하여 브랜드 보고서 생성 |
| Match Rate | **99.3%** (69항목 중 68 MATCH, 1 PARTIAL, 0 MISSING) |
| Iteration | 불필요 (99.3% ≥ 90%) |

## 2. 구현 결과 요약

### 문제 → 해결

| Before (문제) | After (해결) |
|---------------|-------------|
| 슬라이드 레이아웃 항상 blank(6) 고정 | 템플릿의 cover, title_content, blank 등 자동 분류 후 매칭 |
| 색상 하드코딩 (`BRAND_PRIMARY` 등) | `StyleConfig.rgb("accent")` 역할 기반 10종 색상 |
| 좌표 13.333x7.5 인치 절대값 | `style.x(ratio)`, `style.y(ratio)` 비율 좌표 → 4:3/16:9 자동 대응 |
| 플레이스홀더 미사용 | `_find_placeholder()` → 있으면 우선 사용, 없으면 fallback |
| 기존 슬라이드 잔존 | `_remove_existing_slides()` 로 자동 제거 |
| 템플릿 테마 색상 무시 | XML `a:clrScheme` 파싱하여 역할별 매핑 |

### 사용법

```bash
# 기존 방식 (변경 없음)
python generate_report.py --input data.csv --output output/

# 회사 템플릿 적용
python generate_report.py --input data.csv --template 우리회사.pptx --output output/

# 템플릿 분석만
python template_analyzer.py --input 우리회사.pptx
python template_analyzer.py --input 우리회사.pptx --json
```

## 3. 생성/수정 파일

| 파일 | 변경 | LOC |
|------|------|-----|
| `scripts/style_config.py` | **신규** | 97 |
| `scripts/template_analyzer.py` | **신규** | 290 |
| `scripts/create_pptx.py` | **리팩토링** | 530 |
| `scripts/generate_report.py` | **수정** | 120 |
| `scripts/create_sample_templates.py` | **신규** | 50 |
| `samples/template_16x9.pptx` | **신규** | - |
| `samples/template_4x3.pptx` | **신규** | - |

## 4. 아키텍처

```
[사용자]
  │
  ├── --input data.csv
  ├── --template company.pptx  (선택)
  └── --output output/
  │
  ▼
generate_report.py
  │
  ├── Step 0: template_analyzer.py → StyleConfig (신규)
  ├── Step 1: analyze_data.py → analysis dict (기존)
  ├── Step 2: create_pptx.py (StyleConfig 기반 렌더링) (개선)
  └── Step 3: generate_email.py (변경 없음)
```

### 핵심 설계 패턴

1. **역할 기반 색상 시스템** — `pptx-design-styles` 레포에서 차용. 10종 역할(accent, title_text, body_text, card_fill, border, success, warning, muted 등)
2. **폰트 3계층 6레벨** — display(44pt) → heading(28pt) → subhead(20pt) → body(14pt) → caption(11pt) → small(10pt)
3. **플레이스홀더 우선 + fallback** — 템플릿에 플레이스홀더가 있으면 그곳에 삽입, 없으면 비율 좌표로 도형 직접 배치
4. **비율 좌표** — 절대 좌표 대신 `style.x(ratio)`, `style.y(ratio)`로 모든 슬라이드 크기에 대응

## 5. 테스트 결과

| 테스트 | 결과 |
|--------|------|
| 템플릿 없이 실행 (하위 호환) | ✅ 기존과 동일 동작 |
| 16:9 템플릿 적용 | ✅ 레이아웃 5개 감지, 플레이스홀더 사용, 기존 슬라이드 제거 |
| 4:3 템플릿 적용 | ✅ 10.0x7.5 인치 자동 대응, 비율 좌표 적용 |
| 템플릿 분석 CLI | ✅ `--json` 옵션 포함 정상 동작 |

## 6. Plan 요구사항 달성 현황

### 필수 (Must Have)

| ID | 요구사항 | 상태 |
|----|---------|------|
| R1 | 템플릿 분석기 | ✅ `template_analyzer.py` |
| R2 | 플레이스홀더 매핑 | ✅ `_find_placeholder()` + `_apply_placeholder_text()` |
| R3 | 슬라이드 크기 대응 | ✅ `style.x()` / `style.y()` 비율 좌표 |
| R4 | 테마 색상 적용 | ✅ XML `a:clrScheme` 파싱 → 역할 매핑 |
| R5 | 기존 슬라이드 정리 | ✅ `_remove_existing_slides()` |
| R6 | 하위 호환성 | ✅ `default_style()` fallback |

### 선택 (Nice to Have)

| ID | 요구사항 | 상태 |
|----|---------|------|
| N1 | 레이아웃 자동 선택 | ✅ `_classify_layout()` + `_get_layout()` |
| N2 | 폰트 상속 | ✅ `font_family` 추출 및 적용 |
| N3 | 템플릿 프리뷰 | ✅ `print_template_summary()` + `--json` CLI |

## 7. 참고 자료

- Plan: `docs/01-plan/features/doc-automation-template.plan.md`
- Design: `docs/02-design/features/doc-automation-template.design.md`
- Analysis: `docs/03-analysis/doc-automation-template.analysis.md`
- 참고 레포: [pptx-design-styles](https://github.com/corazzon/pptx-design-styles) — 역할 기반 색상/폰트 체계 차용
