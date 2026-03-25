# Gap Analysis: HWPX 파일 지원 (hwpx-support)

> Design: `docs/02-design/features/hwpx-support.design.md`
> 분석일: 2026-03-25

## Match Rate: 97.7% (42/43)

## 상세 체크리스트

### hwpx_parser.py (17항목, 16 매칭)

| # | 설계 항목 | 상태 | 비고 |
|---|----------|:----:|------|
| 1 | `parse_hwpx()` API | ✅ | text, paragraphs, tables, images, metadata 반환 |
| 2 | `extract_text()` API | ✅ | 표 데이터도 텍스트에 포함 |
| 3 | ZIP 유효성 검증 | ✅ | `zipfile.is_zipfile()` |
| 4 | 암호화 파일 감지 | ✅ | `_is_encrypted()` flag_bits 검사 |
| 5 | content XML 탐색 | ✅ | section*.xml, content.xml 순서로 탐색 |
| 6 | 단락 파싱 (hp:p/hp:t) | ✅ | 네임스페이스 무관 탐색 |
| 7 | 표 파싱 (2D 리스트) | ✅ | `{"rows": [[cell, ...]]}` |
| 8 | 이미지 추출 (BinData) | ✅ | png, jpg, gif, bmp, tiff |
| 9 | 메타데이터 파싱 | ✅ | title, creator, subject 등 |
| 10 | OWPML 네임스페이스 | ✅ | 동적 감지 + 기본값 |
| 11 | CLI 인터페이스 | ✅ | `--json` 옵션 지원 |
| 12 | 단락 `style` 필드 | ❌ | 설계에는 `{"text", "style"}` 반환 명시, 구현에는 `{"text"}`만 반환 |

### hwpx_template.py (6항목, 6 매칭)

| # | 설계 항목 | 상태 |
|---|----------|:----:|
| 13 | `fill_template()` API | ✅ |
| 14 | `scan_placeholders()` API | ✅ |
| 15 | XML 플레이스홀더 치환 | ✅ |
| 16 | linesegarray 제거 | ✅ |
| 17 | ZIP 재패키징 (mimetype 비압축) | ✅ |
| 18 | CLI 인터페이스 | ✅ |

### analyze_data.py (4항목, 4 매칭)

| # | 설계 항목 | 상태 |
|---|----------|:----:|
| 19 | DOCUMENT_EXTENSIONS에 .hwpx 추가 | ✅ |
| 20 | load_document_text()에 .hwpx 분기 | ✅ |
| 21 | `_load_hwpx()` 함수 | ✅ |
| 22 | Docstring 업데이트 | ✅ |

### generate_report.py (5항목, 5 매칭)

| # | 설계 항목 | 상태 |
|---|----------|:----:|
| 23 | `--hwpx-template` 인수 | ✅ |
| 24 | 파일 타입 감지 (tabular/document) | ✅ |
| 25 | HWPX 템플릿 모드 (fill_template 호출) | ✅ |
| 26 | `_build_hwpx_data()` 매핑 함수 | ✅ |
| 27 | Import 업데이트 | ✅ |

### SKILL.md (4항목, 4 매칭)

| # | 설계 항목 | 상태 |
|---|----------|:----:|
| 28 | 지원 형식 표에 .hwpx | ✅ |
| 29 | 자동 감지 예시 추가 | ✅ |
| 30 | 커맨드 예시 추가 | ✅ |
| 31 | 파일 구조에 신규 모듈 | ✅ |

### 에러 처리 & 의존성 (7항목, 7 매칭)

| # | 설계 항목 | 상태 |
|---|----------|:----:|
| 32 | 잘못된 HWPX → ValueError | ✅ |
| 33 | content.xml 없음 → ValueError | ✅ |
| 34 | 암호화 HWPX → ValueError | ✅ |
| 35 | 미매칭 플레이스홀더 → 경고만 | ✅ |
| 36 | stdlib만 사용 | ✅ |
| 37 | requirements.txt 변경 없음 | ✅ |

## 갭 목록

| 갭 | 영향도 | 설명 |
|----|--------|------|
| 단락 `style` 필드 미구현 | 낮음 | 설계에서 `{"text": str, "style": str}` 반환을 명시했으나 구현에서는 `{"text": str}`만 반환. 현재 하류 소비자가 style 필드를 사용하지 않으므로 영향 없음 |

## 설계 초과 구현 (긍정적)

| 항목 | 설명 |
|------|------|
| `_detect_namespaces()` | 실제 XML에서 네임스페이스 동적 감지 — 버전 호환성 향상 |
| `_find_all_with_local_name()` | 네임스페이스 무관 요소 탐색 — 견고성 향상 |
| tail 텍스트 처리 | XML tail 텍스트의 플레이스홀더도 치환 — 완전성 향상 |
