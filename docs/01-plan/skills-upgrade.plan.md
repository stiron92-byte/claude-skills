# claude-skills 고도화 분석 및 계획서

> 대상: https://github.com/humanist96/claude-skills (플러그인 `claude-skills-book` v1.6.1, 스킬 8개)
> 작성일: 2026-10-01 · 개정: v2 (사내 전사 배포 + 외부 강의 실습 플러그인 관점 재검토 반영)
> 목적: 8개 스킬을 순차적으로 고도화하기 위한 현황 진단, 외부 레퍼런스 대조, 개선 항목 발굴, 실행 로드맵
> 사용 시나리오: (A) 사내 모든 업무 부서 배포, (B) 외부 강의 실습 플러그인

---

## v2 재검토 요약 — 무엇이 바뀌었나

v1은 "스킬 품질 고도화"에만 초점을 맞췄다. 사내 전사 배포와 외부 강의라는 사용 시나리오를 대입하면 **품질 작업보다 먼저 풀어야 할 배포 차단 이슈**가 있다. v2는 이를 §7에 "Gate 0"으로 추가하고 로드맵 맨 앞에 배치했다.

| # | v1의 빈틈 | 왜 문제인가 | v2 조치 |
|---|-----------|-------------|---------|
| 1 | **라이선스 부재를 다루지 않음** | 저장소에 LICENSE가 없고 GitHub도 라이선스 미지정이다. 원저작자 권리가 그대로 유지되므로 사내 재배포·외부 강의 사용 권한이 불명확하다 | §7.1 법무 게이트 신설, 배포 전 서면 허락 또는 재작성 |
| 2 | **데이터 보호·보안 검토 없음** | 엑셀 고객 개인정보, 회의 녹음, 외부 API(Gemini·YouTube·웹검색) 전송 경로가 정리돼 있지 않다 | §7.2 스킬별 데이터 흐름표, 기본 비활성 정책 |
| 3 | **YouTube 봇 감지 우회·쿠키 추출을 그대로 둠** | 기업 배포 시 플랫폼 약관·저작권 리스크 | §7.1에 generate-shorts 사용 범위 제한 |
| 4 | **샘플 제거 권고가 책 실습을 깨뜨림** | 실습 프롬프트 2-2·2-5는 "플러그인 안의 샘플을 찾아 복사"하라고 지시한다. v1의 D3(skills/에서 샘플 제거)를 따르면 강의가 멈춘다 | 플러그인 3분할(업무/크리에이터/실습)로 해결(§7.3) |
| 5 | **`_shared` 공통 모듈이 개별 설치를 깨뜨림** | README의 수동 설치(스킬 폴더 복사)와 claude.ai 스킬 단위 업로드에는 `_shared`가 따라가지 않는다 | 빌드 단계에서 공통 모듈을 각 스킬로 복사(vendoring) |
| 6 | **스킬 통합·개명 시 하위 호환 없음** | content-research 흡수 시 책 독자 프롬프트·`/claude-skills-book:content-research` 호출이 깨진다 | 리다이렉트 스텁 스킬, 폐기(deprecation) 정책 |
| 7 | **버전 고정·릴리스 채널 없음** | 강의 도중 main이 바뀌면 수강생마다 다른 버전을 받는다 | 태그 릴리스, 마켓플레이스 `ref`/`sha` 고정, stable/dev 채널 |
| 8 | **공급망 관리 없음** | `>=` 의존성, `--break-system-packages`, `curl \| sh`, yt-dlp 자동 업그레이드 | 버전 고정·잠금 파일·사내 미러 |
| 9 | **강의장 장애 모드 미고려** | 수강생 30명이 같은 IP로 YouTube·Gemini·웹검색 호출 시 차단·레이트리밋 | 오프라인 데모 모드, 사전 점검(doctor) 스킬 |
| 10 | **다른 플러그인과의 트리거 충돌 미고려** | 사내 PC에는 공식 xlsx·docx·pptx 스킬, 영업·증권 플러그인 등이 함께 설치된다 | 교차 플러그인 near-miss 트리거 평가 |
| 11 | **성공 기준·일정·담당·리스크 등록부 없음** | 전사 배포 승인과 강의 일정 수립이 불가 | §7.6 KPI·마일스톤·RACI·리스크 |
| 12 | **평가 비용·Windows CI 현실성 누락** | 영상 스킬 평가는 비싸고, `claude plugin eval`은 Windows 네이티브 샌드박스가 없다 | 스모크/풀 태그 분리, 비용 상한, 수동 Windows 매트릭스 |
| 13 | **v1 내부 오류·모순** | 상충하는 description 원칙 병기, "절대 규칙" 일괄 완화가 안전 규칙까지 약화시킬 위험 | §7.7 정오표 |
| 14 | **사용자 맞춤 수정 경로가 없음** | 부서·개인이 스킬을 고치려면 플러그인 설치 폴더를 직접 수정해야 하고, 그 수정은 업데이트 때 사라진다 | §8 커스터마이즈 설계(확장 지점 계약 + 오버라이드 폴더)와 사용자용 방법론 |

---

## 0. 요약 (Executive Summary)

이 저장소는 책 『압도적 스킬로 바로 쓰는 클로드 코워크×AI 자동화』의 실습 스킬 8개를 하나의 플러그인으로 묶어 배포한다. 스킬 설계 자체는 실무 시나리오가 구체적이고(한글 HWPX 치환, 멀티탭 엑셀 취합, 쇼츠 큐레이션 등), "스크립트는 도구, 판단은 Claude"라는 원칙이 일부 스킬(generate-shorts, data-collector)에 잘 녹아 있다.

반면 플러그인 전체 관점에서 보면 다음 구조적 문제가 반복된다.

| # | 문제 | 영향 받는 스킬 | 심각도 |
|---|------|----------------|--------|
| 1 | 실행 환경 가정이 claude.ai 컨테이너(`/mnt/user-data`, `present_files`)에 고정되어 Claude Code·Cowork·Windows에서 지시가 어긋남 | meeting-minutes, data-collector, content-repurpose, narration-video | 높음 |
| 2 | 테스트·평가(evals) 체계가 전무. 스킬 수정 시 회귀를 잡을 방법이 없음 | 전체 | 높음 |
| 3 | 플러그인 매니페스트(`plugin.json`) 부재. 마켓플레이스 owner/URL은 humanist96로 정리 완료(2026-10-01) | 플러그인 전체 | 중간 |
| 4 | Anthropic 공식 스킬(pptx·docx·xlsx·pdf)과의 연계가 경로 하드코딩 또는 구두 언급 수준 | doc-automation, meeting-minutes, excel-automation | 높음 |
| 5 | description이 트리거 키워드 나열형이라 스킬 간 충돌(content-research↔data-collector, doc-automation↔excel-automation 차트, content-repurpose↔generate-shorts 스크립트)이 해소되지 않음 | 5개 스킬 | 중간 |
| 6 | 대용량 바이너리(skills/ 약 23MB, 이 중 doc-automation 예제 docx 6개가 각 2.9MB로 17.7MB)가 배포 스킬 폴더에 포함. 1회성 스크립트 4개는 제거 완료 | doc-automation, meeting-minutes, excel-automation | 중간 |
| 7 | SKILL.md가 점진적 공개(progressive disclosure) 없이 코드·스펙을 본문에 모두 적재(최대 2,300단어) | excel-automation, content-repurpose, data-collector | 중간 |
| 8 | 스크립트가 세션 안에서 Anthropic API를 다시 호출(이중 과금, API 키 필요) | content-research | 중간 |

고도화 방향은 네 축이다(v2에서 0번 추가).

0. **배포 게이트(Gate 0)**: 라이선스·저작권 정리, 데이터 보호·보안 검토, 플러그인 분할·버전 고정. 이것이 끝나기 전에는 사내 배포·외부 강의에 쓰지 않는다(§7).
1. **공통 기반 정비**: 플러그인 매니페스트, 환경 중립적 경로 규약, 공통 레퍼런스, eval 하네스, 배포 슬림화.
2. **스킬별 품질 고도화**: Anthropic skill-creator 원칙(설명은 "무엇+언제", 본문은 lean, 이유를 설명, 스크립트는 반복 작업만)에 맞춰 재작성하고 공식 스킬·외부 유명 스킬의 패턴을 이식.
3. **검증 루프 도입**: 스킬마다 `evals/evals.json` + 트리거 평가 세트를 만들고 skill-creator의 벤치마크·description 최적화 루프를 돌린다.

권장 순차 작업 순서(가치 × 난이도): doc-automation → excel-automation → meeting-minutes → content-repurpose → data-collector(+content-research 통합 검토) → generate-shorts → narration-video.

v2 보정: 사내 배포는 업무 플러그인(doc·excel·meeting·data-collector)부터 순차 공개하고, 크리에이터 플러그인(content·shorts·narration)은 법무 검토(§7.1) 통과 후 선택 설치로 공개한다. 강의는 고정 태그 버전만 사용한다.

---

## 1. 현황 진단

### 1.1 저장소 구조

```
claude-skills/
├── .claude-plugin/marketplace.json   # 플러그인 정의가 인라인(plugin.json 없음)
├── chapter02-* ~ chapter12_*         # 책 챕터 스냅샷(skills/와 중복, 18MB+)
├── docs/                             # bkit PDCA 산출물(과거 2개 기능 계획·설계·보고서)
├── skills/                           # 배포 본체 8개(약 24MB, assets 포함)
└── README.md
```

측정값:

| 스킬 | SKILL.md 단어 수 | description 길이 | frontmatter 필드 | 스크립트 라인 |
|------|-----------------:|-----------------:|------------------|--------------:|
| doc-automation | 1,313 | 132자 | name, description | 약 3,300 |
| excel-automation | 2,143 | 392자 | name, description | 0 (코드 생성형) |
| meeting-minutes | 1,402 | 602자 | name, description | 169 |
| content-research | 636 | 461자 | +allowed-tools, argument-hint | 663 |
| data-collector | 1,807 | 489자 | +allowed-tools, argument-hint | 1,623 |
| content-repurpose | 2,301 | 496자 | name, description | 0 |
| generate-shorts | 1,631 | 387자 | +argument-hint, allowed-tools | 2,572 |
| narration-video | 996 | 243자 | +argument-hint, allowed-tools(MCP 10종) | 2,443 + MCP 서버 |

관찰:

- frontmatter 규약이 스킬마다 다르다. 4개만 `allowed-tools`를 쓰고, `version`·`license`·`compatibility`·`metadata` 필드는 어디에도 없다.
- `evals/`, `tests/`, CI 워크플로가 없다. bkit PDCA 도구 상태 파일(`docs/.pdca-*`, `docs/.bkit-memory.json`)은 작성자 로컬 경로를 담고 있어 삭제하고 .gitignore에 추가했다(2026-10-01).
- 루트에 LICENSE가 없다. GitHub 저장소 메타데이터도 라이선스 미지정이다(§7.1).
- `.gitignore`가 `*.pptx`, `*.png`, `*.mp4`를 제외하지만 `skills/*/assets/`에는 강제 추가된 pptx·docx·hwpx·mp3·xlsx가 있다. 플러그인 설치 시 그대로 내려온다.
- `chapter05-skill-customization/`은 외부 스킬(marketingskills, 34개)을 분석한 문서가 있으나 README는 "작성 예정" 상태다. 이 분석은 외부 스킬 참조 작업의 선례로 재활용 가능하다.

### 1.2 스킬별 진단

각 스킬에 대해 **강점 / 문제 / 고도화 포인트**를 정리한다. 문제의 근거는 해당 SKILL.md와 스크립트에서 직접 확인한 내용이다.

#### (1) doc-automation — 문서·PPT 자동화

강점
- 지원 입력이 넓다(CSV/XLSX/PDF/DOCX/PPTX/HWPX/HTML/MD). 특히 **HWPX 파싱·텍스트 치환(`hwpx_parser.py`, `hwpx_template.py`)**은 국내 업무 환경에서 다른 어떤 공개 스킬에도 없는 차별 자산이다.
- "XML 파서를 쓰면 한컴에서 깨진다 → 문자열 치환만 사용, linesegarray 제거" 같은 실패에서 얻은 도메인 지식이 기록돼 있다.
- 회사 템플릿 분석(`template_analyzer.py`)과 플레이스홀더 우선 배치가 설계돼 있다.

문제
- 파이프라인이 "5장짜리 주간보고(표지·요약·상세·이슈·계획)" 고정 레이아웃이다. 책의 실습(환율 PDF→과장님 보고 PPT, 구글 파이낸스 URL→5장, 회사 문서 6개+공고→기업 PPT)은 사실상 Claude가 자유 구성으로 만드는 것이고 스크립트 파이프라인과 맞지 않는다. 스킬이 "주간보고 스크립트"와 "자유 PPT 생성" 두 역할 사이에서 정체성이 흐리다.
- python-pptx 좌표 배치 결과물은 Anthropic 공식 `pptx` 스킬(pptxgenjs 생성 + 썸네일 시각 QA + 디자인 규칙)보다 디자인 품질이 낮다. 공식 스킬과의 연계 지시가 없다.
- `scripts/`에 1회성 파일이 섞여 있었다. 작성자 로컬 경로가 하드코딩된 `fix_docx.py`, `fix_docx_round2.py`, `fix_captions.py`(원고 교정용), `make_fireworks_report.py`(불꽃축제 보고서 전용)는 skills/와 chapter02 양쪽에서 삭제했다(2026-10-01). `create_sample_templates.py`(테스트 템플릿 생성)는 과거 보고서가 참조하므로 개발용 `tools/`로 이동 대상.
- description이 132자로 가장 짧고 HWPX·템플릿·URL 입력을 언급하지 않아 핵심 트리거를 놓친다.
- "데이터 시각화 — 매출 추이 차트 그려줘"를 트리거로 선언해 excel-automation과 충돌한다.
- `analyze_data.py`의 한글 폰트 탐색이 AppleGothic/Malgun/Nanum 이름 기반이라 Linux 컨테이너에서 실패 시 대체 경로가 없다.

고도화 포인트
- 역할 재정의: **"입력 문서 이해 + 보고 스토리라인 설계 + 렌더링 위임"**. 렌더링은 공식 `pptx` 스킬(pptxgenjs)에 위임하고, 회사 템플릿 플레이스홀더 채우기가 필요할 때만 python-pptx 경로를 쓴다.
- HWPX 기능을 `references/hwpx.md`(또는 독립 스킬 `hwpx-editor`)로 승격해 트리거·설명을 분리한다. 구조는 kangdacool/hwpx-editing-skill을 참고: 변경 없는 ZIP 엔트리를 바이트 그대로 보존하는 repack, `inspect`/`verify` 스크립트, 저장 직후 자동 검증하는 PostToolUse 훅(모델 컨텍스트를 쓰지 않음).
- 보고 대상(과장/팀장/임원)·관점(리스크/타이밍 등) 질의를 구조화하고, 결과물 검수 체크리스트(숫자 출처, 슬라이드당 메시지 1개, 폰트 깨짐)를 추가한다.
- 1회성 스크립트 삭제, `samples/`·`assets/`는 저용량 샘플만 유지하고 나머지는 chapter 폴더나 Release 자산으로 이동.

#### (2) excel-automation — 엑셀 정리·분석·취합

강점
- "원본을 덮어쓰지 않는다", "이상값은 자동 수정하지 않고 후보 시트로 보고한다", "통합관리 시트는 VLOOKUP 수식으로 구성해 원본 변경을 반영한다", "원본 시트 전부 보존" 등 실무 안전 원칙이 명확하다.
- 인사이트를 한글 줄글로 2~4문장 작성하라는 좋은/나쁜 예시가 있다.
- 공식 `xlsx` 스킬의 `recalc.py` 재계산을 요구한다.

문제
- 본문 2,143단어·399줄에 pandas/openpyxl 코드가 모두 인라인이라 점진적 공개 원칙에 어긋난다. 코드는 Claude가 이미 쓸 수 있는 수준이라 본문에 둘 가치가 낮다.
- matplotlib 폰트를 `DejaVu Sans`로 지정해 한글이 깨진다(주석으로만 "조정하라"고 함).
- `recalc.py` 위치가 명시되지 않아 공식 xlsx 스킬이 없는 환경에서는 실패한다. 환경별 대체(LibreOffice 유무)가 없다.
- 대용량(10만 행 이상) 처리 지침이 한 줄뿐이고, 날짜 파싱 `pd.to_datetime` 기본값은 월/일 순서 모호성(01/02/2026)을 다루지 않는다.
- 트리거 "정리해줘", "분석해줘"가 지나치게 일반적이라 엑셀 파일이 없을 때도 오발동 가능.

고도화 포인트
- 코드 블록을 `references/cleaning.md`, `references/analysis.md`, `references/consolidation.md`로 분리하고 본문은 판단 기준·안전 원칙·출력 규격만 남긴다.
- 반복 작업(전화번호·날짜 정규화, 이메일 도메인 오타 탐지, 키 후보 탐색)을 `scripts/excel_utils.py`로 묶어 매번 재작성하지 않게 한다.
- 한글 폰트 탐색 공통 모듈(§3.2)을 사용.
- 검증 단계 추가: 결과 파일을 다시 열어 행 수 보존, 수식 오류(`#N/A`, `#REF!`) 0건, 시트 목록 확인. unlazy 스킬의 Excel 오류셀 체크 오라클과 연계 가능.
- 공식 `xlsx` 스킬을 "있으면 사용, 없으면 openpyxl 직접"으로 조건부 연계.

#### (3) meeting-minutes — 회의록 정리

강점
- 역할(6종) × 용도(4종) 매트릭스와 `references/output-templates.md`로 출력 구조가 체계적이다.
- 파일 크기별 예상 처리 시간 안내, STT 결과 200자 미리보기 검증 등 UX 배려가 있다.
- 샘플 녹음 3개(한/영)가 동봉돼 바로 시험 가능하다.

문제
- 경로가 claude.ai 컨테이너 전용이다: `/mnt/user-data/uploads/`, `/mnt/skills/user/meeting-minutes/...`, `/mnt/skills/public/docx/SKILL.md`, `/home/claude`, `present_files`. Claude Code·Cowork·Windows에서는 지시가 그대로 틀린다.
- 시작 전 질문 3개를 "절대 건너뛰지 않는다"고 강제한다. 이미 맥락이 있거나 "그냥 정리해줘"인 경우 마찰이 크다. 기본값을 제시하고 한 번에 묻거나 `AskUserQuestion`을 쓰는 편이 낫다.
- Whisper `base` 모델은 한국어 정확도가 낮다. `small` 이상 또는 `large-v3-turbo`를 기본 후보로 두고 환경(CPU/GPU, 디스크)에 따라 고르게 해야 한다.
- 화자 분리(diarization)·타임스탬프가 없어 "누가 말했는지"가 추정에 의존한다.
- 완료 후 "이 스킬은 회의록 외에도…" 홍보 문구는 결과물에 노이즈다.
- 액션 아이템 추출 품질 기준(담당자 미상 처리, 기한 없는 항목 표기)이 없다.

고도화 포인트
- 환경 감지 규약(§3.1)으로 경로를 치환. docx 출력은 공식 `docx` 스킬이 있으면 그것을, 없으면 python-docx로.
- 질문을 "기본값 제안 + 한 번에 확인" 방식으로 완화.
- STT: faster-whisper 모델 선택 로직, 긴 파일 분할(`ffmpeg -f segment`), 선택적 화자 분리(pyannote는 무거우므로 옵션).
- 출력 품질 게이트: 결정 사항은 원문 근거 인용, 액션 아이템은 담당자/기한 미상 시 "미정" 표기, 숫자·날짜는 원문 그대로.
- 외부 참조: Anthropic `docx` 스킬(표·목차 생성), 커뮤니티 meeting-notes 스킬들의 "Decisions / Open questions / Parking lot" 구분.

#### (4) content-research — 콘텐츠 리서치

강점
- 질문→config→RSS 수집→분석→브리핑이라는 흐름이 단순하고, 용도별(youtube/blog/newsletter/general) 분석 프롬프트 표가 있다.

문제
- `content_analyzer.py`가 세션 안에서 **Anthropic API를 다시 호출**한다(`claude-sonnet-4-20250514` 하드코딩, `ANTHROPIC_API_KEY` 필요). 사용자는 이미 Claude와 대화 중인데 API 키를 또 받고 이중 과금된다. data-collector는 이미 "수집은 Claude 내장 도구, Python은 로컬 처리만"으로 고쳤으므로 같은 패턴으로 맞춰야 한다.
- RSS 목록이 본문에 하드코딩돼 있고 일부는 유효성이 불확실하다(Bloomberg RSS 등). 네이버·구글 뉴스 등 국내 소스가 없다.
- data-collector와 기능·트리거가 크게 겹친다("트렌드", "뉴스 수집", "시장 브리핑"). 두 스킬의 description이 서로를 구분하려고 애쓰는 것 자체가 설계 신호다.
- 가상환경 생성·pip 설치를 매번 시키는 절차가 Cowork 45초 제한과 충돌한다.

고도화 포인트
- 선택지 A: data-collector에 흡수하고 content-research는 "콘텐츠 기획(아이디어·캘린더·훅)" 전용 후처리 스킬로 축소. 선택지 B: 두 스킬 유지하되 수집 엔진을 공유 모듈로 추출. **A를 권장**(사용자 결정 필요).
- API 재호출 제거, 분석은 Claude가 직접 수행.
- 국내 소스 프로필(네이버 뉴스 검색, 구글 뉴스 RSS `news.google.com/rss/search?q=...&hl=ko`, 요즘IT, GeekNews) 추가.

#### (5) data-collector — 데이터 수집·트렌드 보고서

강점
- 컨테이너 네트워크 제약을 인식해 모드1(Claude 도구 수집)/모드2(독립 실행 패키지 생성)를 분리했다. 이 아키텍처 판단은 정확하다.
- 도메인 프로필 6종(finance/beauty/tech/food/realestate/game), 보고서 구조(과거→현재→미래), 투자 조언 금지, Slack webhook 보안 규칙, GitHub Actions 필수 파일 9종 체크리스트가 구체적이다.

문제
- `analyzer.py`의 센티먼트는 긍정/부정 단어 사전 카운트다. Claude가 직접 읽고 판단하는 쪽이 훨씬 정확하다. 키워드 빈도 역시 한국어 형태소 처리 없이 공백 분리라 품질이 낮다.
- 보고서에 **주장별 출처 링크**를 붙이는 규칙이 없다. 리서치 보고서의 신뢰성은 인용 규율에서 나온다(Anthropic deep-research 패턴 참조).
- `/mnt/user-data/outputs/`, `present_files` 하드코딩.
- 수집량 기준("3건 미만이면 불충분")만 있고 검색 쿼리 확장·중복 제거·날짜 필터 기준이 느슨하다.
- 출력 샘플 29개(`output/HBM_*.md`)가 chapter 폴더에 있어 저장소를 불린다(배포 skills/에는 없음, 양호).

고도화 포인트
- 분석 단계를 "Python 통계(빈도·시계열) + Claude 판단(센티먼트·신호·전망)"으로 재배분.
- 인용 규율: 모든 수치·주장에 `[n]` 각주와 URL, 수집일, 소스 신뢰도 등급.
- 리서치 플랜 → 수집 → 교차 검증 → 작성의 4단계로 재구성(Anthropic `/deep-research` 패턴: 범위가 넓으면 확인 질문 2~3개, 병렬 서브에이전트 검색, 주장 교차 검증, 인용 종합). Claude Code에서는 frontmatter `context: fork` + `agent: Explore`로 수집 단계를 분리 컨텍스트에서 돌려 본 세션 컨텍스트를 아낄 수 있다.
- 모드2 패키지는 템플릿 디렉터리를 통째로 복사하는 방식으로 단순화하고, 생성 후 `python -c "import yaml; ..."`로 config 검증.

#### (6) content-repurpose — 콘텐츠 리퍼포징

강점
- 플랫폼 14종 스펙(글자 수·구조·톤·CTA), 품질 검증(글자 수·원본 충실도·플레이스홀더 스캔), "복사해서 바로 게시 가능한 완성본" 원칙이 명확하다. 감사(audit)·갭 분석 모드까지 갖춘 점은 외부 유사 스킬보다 범위가 넓다.
- 네이버 블로그·브런치 등 국내 플랫폼 스펙이 있다.

문제
- 본문 2,301단어 전부가 항상 로드된다. 플랫폼 스펙은 선택된 플랫폼만 읽으면 되므로 `references/platforms/*.md`로 분리해야 한다.
- 상단의 "외부 파일을 찾지 말고 '파일이 없다'는 말을 하지 마라" 지시는 과거 오류의 흔적이며 스킬의 신뢰성을 떨어뜨린다. 원인(파일 참조 누락)을 고치고 지시는 제거.
- 플랫폼별 **예시(few-shot)**가 없다. 글자 수 한도만으로는 톤이 안정되지 않는다.
- 글자 수 검증을 Claude의 눈대중에 맡긴다. 한글 글자 수·X 가중치(CJK 2배)·바이트 계산은 작은 스크립트로 정확히 할 수 있다.
- "YouTube Shorts 스크립트" 출력이 generate-shorts와 트리거가 겹친다. 역할 경계("대본 작성 vs 영상 생성")를 description에 명시.
- 파일 저장 위치가 "workspace 폴더(Cowork)"·`computer://` 링크로 환경 종속.

고도화 포인트
- 구조: `SKILL.md`(흐름·원칙) + `references/platforms/<platform>.md`(스펙+예시 2개) + `scripts/count_chars.py`(플랫폼별 한도 검증) + `references/hooks.md`(훅 공식 모음).
- 외부 참조: marketingskills `social-content`(플랫폼별 가이드, 훅 공식, 리퍼포징 매트릭스)와 `copy-editing`(7-sweep)을 한국 플랫폼에 맞게 이식. chapter05 분석 문서가 이미 이 매핑을 해뒀다.

#### (7) generate-shorts — 유튜브 쇼츠 생성

강점
- 8개 중 설계 완성도가 가장 높다. "규칙 스코어러는 후보만, 선별·제목·자막은 Claude"라는 역할 분리, Phase 3.5 프레임 검수 루프, Cowork 45초 제한 대응(다운로드/인코딩 분리, 재실행 안전, `--only`), 레이아웃 선택 기준(fit_blur 기본), 원본 자막 구운 영상 대응, 카드뉴스 모드까지 실전 피드백이 축적돼 있다.

문제
- 한글 폰트 경로가 Linux/macOS 전용이고 Windows(`C:\Windows\Fonts\malgun.ttf`) 분기가 없다. ffmpeg `drawtext` 경로 이스케이프도 Windows에서 깨지기 쉽다.
- 입력이 YouTube URL만이다. 로컬 mp4·자막 없는 영상(faster-whisper 옵션) 경로가 없다.
- yt-dlp 봇 감지 우회가 환경 변수·쿠키에 의존하며 실패 시 사용자 안내가 reference.md에만 있다.
- 평가 기준(쇼츠가 "좋다"의 정의)이 체크리스트 4개뿐. 후크 길이·자막 타이밍 오차·오디오 피크 등 자동 검사 가능한 항목을 스크립트화할 수 있다.
- `allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task`로 넓게 열려 있다(필요한 범위로 축소).

고도화 포인트
- 크로스플랫폼 폰트·경로 모듈 공유(§3.2), Windows 테스트.
- 입력 확장: 로컬 파일, 자막 없음 → faster-whisper(선택 설치).
- `scripts/verify_short.py`: 해상도 1080x1920, 길이 15~60초, 자막 이벤트 범위 초과 0건, 오디오 존재를 자동 검증해 Phase 3.5 부담을 줄임.
- evals: 공개 강의 영상 1개로 highlights.json 스키마 검증 + 결과 mp4 메타 검증.

#### (8) narration-video — 나레이션 영상

강점
- MCP 서버로 호스트 머신에서 실행하는 구조는 컨테이너 제약을 우회하는 영리한 해법이다. 스타일 프리셋 10종, 콘텐츠 유형별 프리셋 표, 로컬 직접 실행 경로가 있다.

문제
- 진입 장벽이 가장 높다(uv + Gemini API 키 + MCP 등록 + Desktop 재시작). README도 "자동 활성화하지 않았다"고 적고 있다.
- "MCP 도구가 없으면 fallback 절대 금지"는 사용자 입장에서 지나치게 경직돼 있다. 무료 경로(edge-tts + Pillow 카드 배경 또는 단색/그라데이션 + ffmpeg)가 generate-shorts 카드뉴스 모드에 이미 있으므로 "라이트 모드"로 제공 가능하다.
- Gemini 모델 ID(`gemini-2.5-flash-preview-tts`, `gemini-2.0-flash-exp` 등)가 스크립트·MCP 서버·reference·config에 흩어져 있어 모델 폐기 시 여러 곳을 고쳐야 한다.
- 자막 타이밍을 Gemini 오디오 분석에 의존(Phase 4)한다. TTS 응답의 길이 정보나 word boundary(edge-tts 지원)로 더 안정적으로 만들 수 있다.
- 출력 경로 `~/Desktop/narration_output` 고정. 프롬프트 안에 "3초 간격 호출" 같은 레이트리밋 로직이 들어 있어 MCP 서버 쪽으로 옮기는 게 맞다.
- `allowed-tools`에 MCP 도구 10종을 나열해 다른 환경에서 경고가 난다.

고도화 포인트
- 두 가지 모드: Full(Gemini MCP) / Lite(edge-tts + 정적 배경, API 키 불필요).
- README의 "자동 활성화하지 않았다" 의도는 frontmatter `disable-model-invocation: true`로 정식 표현할 수 있다(사용자가 `/narration-video`로만 호출, description은 Claude에게 숨김). 자동 트리거를 유지하려면 Lite 모드가 전제돼야 한다.
- Gemini API 키는 플러그인 `userConfig`(`sensitive: true`)로 받아 MCP 서버 env에 `${user_config.gemini_api_key}`로 주입하면 Desktop 설정 파일을 손으로 고치는 단계를 없앨 수 있다. MCP 서버 정의도 플러그인 `.mcp.json`에 넣어 설치와 함께 등록.
- 모델 ID를 `templates/config.yaml` 단일 출처로 통일, MCP 서버가 config를 읽도록.
- 레이트리밋·재시도는 MCP 서버 내부로 이동.
- 자막 타이밍은 TTS duration 비례 분할을 기본, Gemini 분석은 정밀 옵션.

### 1.3 스킬 간 경계 충돌 맵

| 요청 예 | 현재 트리거 가능 스킬 | 권장 담당 |
|---------|----------------------|-----------|
| "매출 데이터로 차트 그려줘" | doc-automation, excel-automation | 파일이 xlsx/csv고 산출물이 엑셀이면 excel-automation, PPT/보고서면 doc-automation |
| "반도체 트렌드 알려줘" | content-research, data-collector | data-collector |
| "유튜브 주제 뽑아줘" | content-research, data-collector | content-research(기획) |
| "이 영상으로 쇼츠 스크립트 써줘" | content-repurpose, generate-shorts | 대본만이면 content-repurpose, mp4 생성이면 generate-shorts |
| "회의 내용을 PPT로" | meeting-minutes, doc-automation | meeting-minutes → doc-automation 순차(체이닝 규칙 필요) |

description 재작성 시 위 표의 "권장 담당"을 양쪽 description에 상호 배타적으로 명시한다.

---

## 2. 외부 레퍼런스 대조

> Anthropic 공식 자료(2026-10-01 기준 최신 문서)와 커뮤니티 스킬 컬렉션을 조사해 "무엇을 가져올지"를 정한다. 출처 목록은 §2.5.

### 2.1 Anthropic 공식 — Agent Skills 스펙·베스트 프랙티스에서 가져올 원칙

로컬 설치된 공식 `skill-creator`, `plugin-dev/skill-development` 스킬과 공식 문서(platform.claude.com, code.claude.com, agentskills.io 스펙)에서 확인한 규칙:

1. **description이 트리거의 전부**. "무엇을 하는지 + 언제 쓰는지"를 3인칭으로 담는다. Claude는 스킬을 덜 쓰는(undertrigger) 경향이 있으므로 약간 "pushy"하게 쓴다. 본문의 "활성화 상황" 표는 트리거 후에야 로드되므로 트리거에 기여하지 않는다. 공식 예: `Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.`
2. **frontmatter 제약**: `name`은 64자 이하 소문자·숫자·하이픈, **디렉터리명과 일치**, "anthropic"·"claude" 포함 금지. `description` 1,024자 이하. 선택 필드 `license`, `compatibility`(1~500자, 환경 요구사항이 있을 때만), `metadata`(문자열 맵, 예: `{author, version}`), `allowed-tools`. Claude Code 전용 추가 필드: `when_to_use`(description과 합쳐 1,536자 상한), `argument-hint`, `disable-model-invocation`(사용자만 `/호출`), `user-invocable: false`, `allowed-tools`/`disallowed-tools`, `model`, `effort`, `context: fork` + `agent`, `paths`, `shell`, `hooks`. 치환 변수 `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`.
3. **점진적 공개**: metadata(항상, 약 100토큰) → 본문(트리거 시, 5k 토큰 이하·500줄 이하) → 리소스(필요 시). 참조 파일은 SKILL.md에서 한 단계 깊이까지만. **자동 컴팩션 후에는 각 스킬의 첫 5,000토큰만 다시 붙는다**(합계 25,000). 본문이 길면 뒷부분 지시가 사라지는 셈이다.
4. **"Claude는 이미 똑똑하다"**: Claude가 모르는 맥락만 적는다. 문단마다 "이 토큰 비용을 정당화하는가"를 묻는다. 자유도(degrees of freedom)를 작업 성격에 맞춘다: 맥락 의존 작업은 휴리스틱(높음), 깨지기 쉬운 순서는 정확한 스크립트(낮음, "이 명령을 수정하지 마라").
5. **이유를 설명하라**: ALL CAPS·"절대"·"반드시"가 많으면 노란 신호. 현재 스킬들은 "절대 규칙" 섹션이 많다.
6. **피드백 루프를 내장**: "검증기 실행 → 오류 수정 → 반복, 통과 전에는 진행하지 않는다". 파괴적·일괄 작업은 plan-validate-execute(중간 `changes.json`). 검증 오류 메시지는 장황하게.
7. **스크립트 원칙**: "Solve, don't defer"(스크립트가 오류를 직접 처리), 근거 없는 상수(voodoo constants) 금지, 실행 의도 명시("`analyze_form.py`를 실행하라" vs "알고리즘은 … 참고"), 렌더링해 이미지로 검수. Windows 백슬래시 경로 금지, 필요 패키지 명시.
8. **평가 주도 개발**: "광범위한 문서를 쓰기 **전에** 평가를 만든다". 스킬 없이 실패하는 시나리오 3개 → 베이스라인 → 최소 지시 → 반복. 최종 체크리스트에 "평가 3개 이상, Haiku/Sonnet/Opus로 테스트" 포함. Claude A가 쓰고 fresh한 Claude B가 테스트.
9. **skill-creator 루프**: `evals/evals.json` → with-skill vs baseline 동시 실행 → grader(`grading.json`: `text/passed/evidence`) → `aggregate_benchmark` → `generate_review.py` 뷰어 → 피드백 → 개선. 트리거 평가(should/should-not 각 8~10, near-miss 중심) → `run_loop.py`로 description 최적화(`claude -p` 필요). Cowork에서는 `--static` 뷰어.
10. **네이밍**: 동명사형 권장(`processing-pdfs`), `helper`·`utils`·`documents` 같은 모호한 이름 지양. 현재 이름(`doc-automation` 등)은 책과 일치시켜야 하므로 유지하되 description으로 보완.

현재 저장소에 결여된 것: 8·9(전부), 3(3개 스킬 초과), 2(version/compatibility/metadata 없음), 5(문체), 6(검증 루프가 generate-shorts에만 있음).

### 2.2 Claude Code 플러그인 공식 규약

- **`plugin.json`**: `.claude-plugin/plugin.json`, 필수는 `name`뿐이나 `version`·`description`·`author`가 없으면 `claude plugin validate` 경고. 컴포넌트 경로는 `./`로 시작하고 루트 안에 있어야 한다. `license`(SPDX), `keywords`, `homepage`, `repository`, `userConfig`(사용자 설정 스키마: `type`, `title`, `description`, `sensitive: true` → `${user_config.KEY}`로 참조) 지원.
- **마켓플레이스**: 플러그인 entry `name`은 manifest `name`과 같아야 설치가 된다. `strict`(기본 true)는 manifest와 entry 불일치를 막는 옵션. 현재 저장소는 `strict: false`로 plugin.json 없이 운영 중.
- **검증**: `claude plugin validate ./plugin`(`--strict`로 CI), `claude --plugin-dir ./plugin`로 로컬 테스트, `/reload-plugins`, `/skill-doctor`(스킬별 컨텍스트 비용·미사용 스킬 보고).
- **제약**: 플러그인 루트 `CLAUDE.md`는 로드되지 않고 경고. `bin/`이 있으면 claude.ai/Cowork에서 설치 거부. `${CLAUDE_PLUGIN_ROOT}`는 업데이트마다 바뀌므로 상태 저장은 `${CLAUDE_PLUGIN_DATA}`에.
- **hooks**: `hooks/hooks.json`(`PostToolUse` `matcher: Write|Edit` 등). 플러그인 훅은 세션 로드 시부터 발화하므로 matcher로 좁힌다.
- **공식 평가 명령 `claude plugin eval`**(v2.1.269+): `evals/<case>/prompt.md`(+ frontmatter `max_turns`, `runs`, `tags`, `model`) + `graders/*.md`(`regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`). 플러그인 유/무 각 3회(ablation) 실행해 Δ를 보고, `--threshold`로 CI 게이트. "Δ≈0이고 `tool_used: Skill` grader 실패"가 가장 흔한 첫 발견이며 description 조정을 의미한다. `llm` 판정자는 바이너리(pptx/pdf)를 거부하므로 텍스트·이미지로 렌더링 후 평가. Windows 네이티브는 샌드박스 백엔드가 없어 WSL2 필요. skill-creator의 `evals.json`과는 서로 호환되지 않으므로 둘을 역할 분담: **skill-creator 루프 = 사람 리뷰 기반 질적 반복, `claude plugin eval` = CI 회귀 게이트**.

### 2.3 Anthropic 공식 문서 스킬(docx / pptx / xlsx / pdf)과의 연계

| 공식 스킬 | 현재 구현 | 연계 대상 | 연계 방식 |
|-----------|-----------|-----------|-----------|
| `pptx` | **pptxgenjs**(Node)로 생성, OOXML 직접 편집, `markitdown`으로 읽기, `thumbnail.py`·`validate.py`·soffice 렌더 QA. 디자인 규칙: 토픽 팔레트, 슬라이드마다 시각 요소, 제목 36~44pt/본문 14~16pt, "AI 흔적"(제목 밑 액센트 라인·색 막대) 회피 | doc-automation | 자유 구성 PPT는 공식 스킬 절차에 렌더링 위임. 회사 템플릿 플레이스홀더 채우기만 자체 python-pptx 유지. 공식 스킬의 디자인 규칙·시각 QA를 doc-automation 검수 체크리스트에 흡수 |
| `docx` | `docx` npm으로 생성, OOXML 편집, `validate.py`(XSD), 추적 변경 `<w:ins>/<w:del>`, `pandoc -t markdown` 읽기 | meeting-minutes, doc-automation | 출력이 docx면 공식 스킬 지침을 먼저 읽도록 조건부 참조 |
| `xlsx` | openpyxl + `recalc.py`(LibreOffice). "수식을 쓰고 Python 계산값을 하드코딩하지 마라", 수식 오류 0건, `_xlfn.` 접두, XLOOKUP/FILTER/UNIQUE 금지(LibreOffice 미지원) | excel-automation | 수식 재계산·검증 위임. **현재 excel-automation의 VLOOKUP 원칙과 공식 규칙이 일치**하므로 금지 함수 목록만 추가. 공식 스킬 부재 시 LibreOffice 유무 확인 후 대체 |
| `pdf` | pdfplumber·폼 채우기 | doc-automation | PDF 추출 경로를 공식 패턴과 맞춤 |

주의: 공식 문서 스킬 4종은 "source-available, 데모·교육 목적" 라이선스다. 코드를 복사하지 말고 **절차와 규칙을 참조**하는 방식으로 연계한다.

연계 규약(공통): "환경에 `<skill>` 스킬이 있으면 그 지침을 읽고 따른다. 없으면 `references/fallback-<format>.md`의 최소 절차를 따른다." 경로 하드코딩(`/mnt/skills/public/...`) 금지.

### 2.4 커뮤니티 유명 스킬에서 가져올 패턴

| 출처 | 가져올 패턴 | 적용 대상 |
|------|-------------|-----------|
| **obra/superpowers `writing-skills`** | "description = 언제 쓰는가(증상·문제), 무엇을 하는가가 아님"(워크플로를 요약하면 모델이 본문 대신 description을 따라감). **합리화 표(rationalization table)**와 **Red flags** 목록으로 단계 건너뛰기 차단. 스킬 작성 전 서브에이전트로 실패 시나리오(RED) 확인. 단어 예산(자주 로드되는 스킬 <200단어, 일반 <500단어). `@` 링크 대신 이름으로 상호 참조 | 전체(특히 "질문 건너뛰기", "검수 생략" 같은 반복 실패 지점) |
| **superpowers `hooks.json`** | `SessionStart` 훅으로 부트스트랩 주입, "Evidence over claims" | Phase 2 훅 검토 |
| **kangdacool/hwpx-editing-skill** | `references/hwpx-guide.md`, `scripts/hwpxlib.py`·`inspect_hwpx.py`·`verify.py`·`audit_layout.py`, **raw-preserving repack**(변경 없는 ZIP 엔트리는 바이트 동일 유지), `hwpx_guard.py` **PostToolUse 훅**으로 모델 컨텍스트 소모 없이 검증 | doc-automation HWPX 분리 시 구조·검증 모델로 채택(라이선스 MIT, 패턴 참조) |
| **AgriciDaniel/claude-youtube** | `SKILL.md` 오케스트레이터 + `sub-skills/`(shorts, repurpose 등 14) + `references/` + `templates/`(채널 보이스) + `execution/` 스크립트. 참조 문서에 발행일 태깅 | content-repurpose 구조(platforms/ 분리), generate-shorts·content-repurpose 경계 |
| **Jakeschincariol/youtube-agent-skill** | `hookscore.py`(실제 훅 74개로 보정, "휴리스틱이지 예측기가 아님"), `/yt-edit`(SRT → 데드에어·필러 편집 리스트), `templates/voice.md` | generate-shorts 후보 스코어러 보정, 훅 라이브러리 |
| **claude-office-skills `meeting-notes`** | 액션 아이템 마커("We need to", "~하기로"), 결정 마커, 담당자 배정 규칙(명시 이름 → 역할 → 모호하면 플래그), 한계(limitations) 섹션 | meeting-minutes 품질 게이트 |
| **xiaosongz/meeting-documenter** | `split-audio.sh`(무음 기준 분할), `compress-audio.sh`, `KNOWN_SPEAKERS.yaml`·`PROJECT_KEYWORDS.yaml`, 발행 전 "source fidelity" 검증 | meeting-minutes 긴 파일 처리·용어 사전 |
| **Anthropic `/deep-research` 패턴** | 범위가 넓으면 2~3개 확인 질문 → 병렬 서브에이전트 검색 → 주장 교차 검증 → 인용 포함 종합. 공식 예시 frontmatter `context: fork`, `agent: Explore` | data-collector 재설계 |
| **marketingskills (chapter05 분석)** | 공통 컨텍스트 스킬(`product-marketing-context`)을 모든 스킬의 입력으로, `social-content`의 플랫폼 가이드·훅 공식·리퍼포징 매트릭스, `copy-editing` 7-sweep | content-repurpose, content-research(`brand-context` 공유) |
| **awesome-claude-skills 류 큐레이션 기준** | "verified" 조건: 6개월 내 커밋, 명확한 사용 사례, 보안 리뷰, 예시·크로스플랫폼 테스트. `README`에 입출력 예시, `CHANGELOG` | Phase 3 배포 |
| **SkillsMP 마켓플레이스** | 유효한 `marketplace.json`이 있는 저장소에 "Marketplace Ready" 배지 | plugin.json 정비 후 자동 노출 |

### 2.5 출처

Anthropic 공식
- Agent Skills 개요·베스트 프랙티스: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview , https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Agent Skills 스펙: https://agentskills.io/specification , 검증 도구 https://github.com/agentskills/agentskills/tree/main/skills-ref
- Claude Code 스킬 frontmatter: https://code.claude.com/docs/en/skills
- 플러그인: https://code.claude.com/docs/en/plugins , https://code.claude.com/docs/en/plugins-reference , https://code.claude.com/docs/en/plugin-marketplaces , https://code.claude.com/docs/en/plugins/marketplace-reference
- 플러그인 평가: https://code.claude.com/docs/en/plugin-evals
- 공식 스킬 저장소: https://github.com/anthropics/skills (skill-creator, pptx, docx, xlsx, pdf, mcp-builder 등 19개; `spec/agent-skills-spec.md`, `template/SKILL.md`)
- 로컬 설치본: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator`, `.../plugins/plugin-dev`(skill-development, hook-development, plugin-structure, skill-reviewer 에이전트)

커뮤니티
- obra/superpowers: https://github.com/obra/superpowers (`skills/writing-skills`, `skills/test-driven-development`, `hooks/hooks.json`)
- kangdacool/hwpx-editing-skill: https://github.com/kangdacool/hwpx-editing-skill
- AgriciDaniel/claude-youtube: https://github.com/AgriciDaniel/claude-youtube
- Jakeschincariol/youtube-agent-skill: https://github.com/Jakeschincariol/youtube-agent-skill
- claude-office-skills/skills meeting-notes: https://github.com/claude-office-skills/skills/blob/main/meeting-notes/SKILL.md
- xiaosongz/meeting-documenter: https://github.com/xiaosongz/meeting-documenter
- hesreallyhim/awesome-claude-code: https://github.com/hesreallyhim/awesome-claude-code
- ComposioHQ/awesome-claude-skills: https://github.com/ComposioHQ/awesome-claude-skills , karanb192/awesome-claude-skills: https://github.com/karanb192/awesome-claude-skills
- SkillsMP: https://skillsmp.com/
- 기타 HWPX 스킬(비교용): Steven-A3/HWPX-CLAUDE-SKILL, KimHands/hwpx-toolkit, airmang/hwpx-skill, adover134/korean_official_document_parser_skill
- marketingskills 분석: 저장소 내 `chapter05-skill-customization/marketingskills-analysis-kr.md`

조사 시 참고: `docs.claude.com` 경로는 `platform.claude.com`/`code.claude.com`으로 리다이렉트된다. 일부 raw GitHub 경로(ComposioHQ README, inferen-sh content-repurposing)는 404여서 HTML 페이지·마켓 목록으로 대체 확인했다.

---

## 3. 공통 기반 설계 (Phase 0)

### 3.1 환경 중립 규약

`skills/_shared/references/environment.md`에 다음을 정의하고, 빌드 단계에서 각 스킬의 `references/`로 복사한다(§3.2 vendoring).

| 항목 | 규칙 |
|------|------|
| 입력 파일 | 사용자가 첨부·경로 지정한 파일. `/mnt/user-data/uploads`는 claude.ai에서만 존재하므로 "첨부 파일 또는 사용자가 지정한 경로"로 서술 |
| 출력 위치 | 현재 작업 폴더의 `output/<스킬명>/` 기본. claude.ai면 `/mnt/user-data/outputs/`, Cowork면 작업 폴더 |
| 결과 전달 | `present_files`가 있으면 사용, 없으면 경로를 마크다운 링크로 안내 |
| 공식 스킬 참조 | 이름으로 참조("docx 스킬이 있으면"), 경로 하드코딩 금지 |
| 명령 시간 제한 | 45초 제한 환경(Cowork) 감지 시 단계 분할·캐시·재실행 안전 |
| OS | Windows/macOS/Linux 분기(폰트·경로·셸) |

### 3.2 공통 스크립트

- `_shared/scripts/fonts.py`: 한글 폰트 탐색(Windows malgun/NanumGothic, macOS AppleGothic/AppleSDGothicNeo, Linux Noto CJK/Nanum, fc-list 폴백), matplotlib/Pillow/ffmpeg용 경로 반환.
- `_shared/scripts/env.py`: 실행 환경(claude.ai/Code/Cowork, OS, 시간 제한 여부) 감지 → JSON.
- `_shared/scripts/paths.py`: 출력 폴더 결정.

플러그인 스킬은 SKILL.md 본문에 `${CLAUDE_PLUGIN_ROOT}`를 써서 플러그인 루트를 참조할 수 있다. 이 변수는 Bash 도구 환경 변수로는 주어지지 않고 본문 치환으로만 들어오므로, 명령 예시는 본문에 경로를 펼쳐 쓴다.

**v2 수정 — 공통 모듈은 소스에서만 공유하고 배포물에는 복사한다.** `_shared`를 런타임에 참조하면 다음 경로에서 깨진다.

| 배포 경로 | `_shared` 런타임 참조 시 |
|-----------|--------------------------|
| 플러그인 설치(Claude Code·Cowork) | 동작 |
| README 수동 설치(스킬 폴더만 복사) | 실패 |
| claude.ai 스킬 업로드(스킬 단위 zip) | 실패 |
| 사내 개별 스킬 배포 | 실패 |

따라서 `tools/build.py`가 `_shared/`를 각 스킬의 `scripts/_vendor/`로 복사하고, CI가 "소스와 복사본이 동일한지"를 검사한다. 스킬은 항상 자기 폴더 안의 사본만 참조한다.

### 3.3 플러그인 매니페스트·배포 슬림화

- `.claude-plugin/plugin.json` 신설(name, version, description, author, homepage, repository, license, keywords). `marketplace.json`의 entry `name`은 manifest `name`과 일치시키고 `strict`를 기본값(true)으로 되돌린다. owner·URL은 humanist96로 갱신 완료. 출처·저작권 고지는 §7.1 권리 정리 결과에 따라 LICENSE·NOTICE로 처리한다. `claude plugin validate . --strict`가 통과해야 한다.
- 플러그인 루트에 `CLAUDE.md`를 두지 않는다(로드되지 않고 경고). `bin/`을 두지 않는다(claude.ai/Cowork 설치 거부).
- narration-video용 `.mcp.json`과 `userConfig`(Gemini 키)를 플러그인 수준에 정의.
- ~~대용량 샘플을 skills/에서 제거~~ → **v2 수정**: 강의 실습 프롬프트가 플러그인 안의 샘플을 찾도록 설계돼 있으므로 제거하지 않고 **실습 전용 플러그인으로 이동**한다(§7.3). 업무 플러그인에는 샘플을 두지 않는다. 예제 docx 6개는 각 2.9MB인데 대부분 내장 이미지이므로 이미지 압축으로 먼저 줄인다.
- 1회성 스크립트 제거(완료).
- `docs/.pdca-*`, `docs/.bkit-memory.json` 삭제·.gitignore 처리(완료).

### 3.4 평가 하네스 (2층 구조)

**1층 — 질적 반복(skill-creator 루프, 로컬)**
- 각 스킬에 `evals/evals.json`(프롬프트 3~5개, 입력 파일, assertions)과 `evals/trigger-eval.json`(should/should-not 각 8~10개, near-miss 중심). 책 실습 프롬프트(PROMPT.MD)를 프롬프트 후보로 우선 채택해 독자 호환을 보장.
- with-skill vs baseline(현행 스냅샷) 실행 → grader → `generate_review.py --static` 뷰어로 사람 리뷰 → 개선. 결과 `evals/benchmark.md` 커밋.
- description 최적화는 `run_loop.py`(`claude -p` 사용)로 스킬 완성 후 1회.

**2층 — 회귀 게이트(`claude plugin eval`, CI)**
- 플러그인 루트 `evals/<case>/prompt.md` + `graders/*.md`. 케이스당 최소 한 쌍: 결과 grader(`file_exists`, `regex`로 산출 파일 내용 검사) + 과정 grader(`tool_used`/`tool_order`). 스킬 발화 grader(`tool_used: Skill`, `input_match`에 스킬명)는 점수 제외지만 "description이 자연어 요청을 못 잡는다"는 가장 흔한 첫 발견을 드러낸다.
- pptx/docx/xlsx 산출물은 `llm` 판정자가 바이너리를 거부하므로 `markitdown`·`pandoc`·openpyxl로 텍스트화한 뒤 `regex` grader 사용.
- CI 예: `claude plugin eval . --trust-plugin --json results.json --threshold 0.8 --max-cost-usd 20`. Windows 네이티브는 샌드박스 백엔드가 없으므로 WSL2 또는 Linux 러너.

**정적 검사(둘 다에 선행)**
- 루트 `scripts/validate_skills.py`: frontmatter 필수 필드·길이(name 64자, description 1,024자, `name`=디렉터리명), 참조 파일 존재, 하드코딩 경로 금지어(`/mnt/`, `present_files`, `~/Desktop`, `computer://`, `/home/claude`) 검출, 본문 500줄 상한, Windows 백슬래시 경로 검출. 공식 `skills-ref validate`와 `claude plugin validate --strict`도 함께 실행.
- GitHub Actions: 정적 검사 + `python -m py_compile` + 스크립트 단위 테스트(hwpx 치환 라운드트립, 전화번호·날짜 정규화, 글자 수 계산, 폰트 탐색 등 순수 함수).

### 3.5 문서 규약

- SKILL.md 공통 골격(superpowers `writing-skills` + 공식 베스트 프랙티스 절충): 개요(1~2문장) → 언제 쓰는가/쓰지 않는가 → 워크플로(단계별, 왜 필요한지 1줄, 복사 가능한 체크리스트) → 출력 규격(템플릿) → 품질 게이트(검증기 실행 → 수정 → 반복) → 합리화 표(건너뛰기 쉬운 단계와 그 핑계·결과) → 참고 파일(한 단계 깊이). 본문 500줄·약 2,000단어 이하. 컴팩션 후 첫 5,000토큰만 남으므로 핵심 규칙을 앞쪽에.
- frontmatter: `name`(디렉터리명과 동일), `description`(무엇+언제+경계, 3인칭, 300~600자), `allowed-tools`(최소), `compatibility`(ffmpeg·LibreOffice·uv 등 환경 요구가 있을 때만), `metadata: {author, version, book-chapter}`, 필요 시 `argument-hint`, `disable-model-invocation`, `context: fork` + `agent`.
- 시간에 묶인 정보(모델 ID, RSS URL, 플랫폼 글자 수 한도)는 본문이 아닌 `references/`·config에 두고 확인일을 적는다.
- **v2 보정 — description 원칙 충돌 해소**: 공식 문서는 "무엇 + 언제"를, superpowers는 "언제만"을 권한다. 공식 규칙을 우선하되 superpowers의 경고를 반영한다. 즉 "무엇"은 결과물 한 줄로 제한하고 워크플로 단계는 description에 쓰지 않는다. 형식: `[결과물 한 줄]. [언제 쓰는가: 상황·파일 형식·한국어 표현]. [쓰지 않는 경우: 담당 스킬명].`
- **v2 보정 — "절대 규칙" 완화의 범위**: 이유를 설명하는 문체로 바꾸는 것은 작업 절차 규칙에만 적용한다. 다음 안전 규칙은 이유를 덧붙이되 강제 표현을 유지한다: 원본 파일 덮어쓰기 금지, API 키·Webhook을 파일에 쓰지 않기, 투자 매수·매도 권유 금지, 개인정보 외부 전송 전 확인, 이상값 자동 수정 금지.
- 각 스킬 `README.md`(사람용): 데모 입출력, 요구사항, 변경 이력.

---

## 4. 실행 로드맵

### Gate 0 — 배포 차단 이슈 해소 (v2 신설, 모든 작업에 선행)

1. 라이선스·저작권: 원저작자 서면 허락 확보 또는 재작성 범위 확정, LICENSE·NOTICE 결정(§7.1)
2. 샘플 자산 재배포 권한 확인(FX 주간 리포트 PDF 등 제3자 저작물)
3. 스킬별 데이터 흐름표 작성, 정보보호팀 검토(§7.2)
4. generate-shorts 사용 범위·쿠키 추출 기본 비활성 결정
5. 플러그인 분할 구조와 릴리스 채널 확정(§7.3)

### Phase 0 — 공통 기반 (선행, 1회)

1. plugin.json 신설, marketplace 정리, owner 갱신, `claude plugin validate --strict` 통과
2. `_shared/` 공통 레퍼런스·스크립트 도입 + `tools/build.py` 복사(vendoring)
3. `scripts/validate_skills.py` + GitHub Actions + `claude plugin eval` 케이스 골격(`evals/`)
4. 배포 슬림화(샘플은 실습 플러그인으로 이동, 1회성 스크립트·도구 상태 파일은 삭제 완료)
5. SKILL.md 골격 템플릿·README 템플릿·합리화 표 템플릿 확정
6. 현행 8개 스킬 스냅샷(`<skill>-workspace/skill-snapshot/`)을 떠서 이후 모든 비교의 baseline으로 고정
7. 의존성 버전 고정(`==`)·잠금 파일, 사전 점검 스크립트(`doctor`) 골격
8. v1.6.1 태그를 "책 호환 고정판"으로 남기고 이후 작업은 v2 브랜치에서 진행
9. 커스터마이즈 확장 지점 계약과 오버라이드 탐색 규약 확정(§8.2), `_shared/references/overrides.md` 작성

### Phase 1 — 스킬별 고도화 (순차)

각 스킬은 동일한 6단계로 진행한다.

```
① 현행 스냅샷 보존(baseline) → ② evals.json 작성(프롬프트 3~5, 책 실습 프롬프트 포함) → ③ 스킬 없이/현행 스킬로 실패 시나리오 확인(RED)
→ ④ SKILL.md·references 재작성 → ⑤ 스크립트 정리·공통 모듈 적용 → ⑥ with-skill vs baseline 실행·뷰어 리뷰(GREEN)
→ ⑦ 트리거 평가 + description 최적화 → ⑧ `claude plugin eval` 케이스 추가(회귀 게이트)
```

| 순서 | 스킬 | 핵심 변경 | 예상 규모 |
|-----:|------|-----------|-----------|
| 1 | doc-automation | 역할 재정의(이해·설계·위임), 공식 pptx 연계, HWPX 분리, 1회성 스크립트 제거, 검수 체크리스트 | 대 |
| 2 | excel-automation | 코드→references 분리, `excel_utils.py`, 한글 폰트, 결과 검증 게이트, xlsx 조건부 연계 | 중 |
| 3 | meeting-minutes | 환경 중립 경로, 질문 완화, STT 모델·분할·화자 옵션, 품질 게이트, docx 조건부 연계 | 중 |
| 4 | content-repurpose | platforms/ 분리 + few-shot, `count_chars.py`, 훅 라이브러리, generate-shorts 경계, 불필요 지시 제거 | 중 |
| 5 | data-collector (+content-research) | 통합 결정, 인용 규율, Claude 판단/Python 통계 재배분, 국내 소스, API 재호출 제거 | 대 |
| 6 | generate-shorts | Windows 폰트·경로, 로컬 입력, `verify_short.py`, allowed-tools 축소 | 중 |
| 7 | narration-video | Lite 모드, 모델 ID 단일화, 레이트리밋 서버 이동, 자막 타이밍 안정화 | 대 |

### Phase 2 — 플러그인 수준 기능

- 스킬 체이닝 규칙: meeting-minutes → doc-automation, data-collector → doc-automation, content-research → content-repurpose. 각 스킬 말미에 "다음으로 가능한 작업"을 표준 문구로.
- 선택: `hwpx-editor` 독립 스킬, `brand-context` 공유 스킬, Cowork 디스패치(chapter11) 예제를 스킬로.
- 선택: hooks(예: 출력 파일 생성 후 자동 검증 스크립트 실행), agents(리서치 서브에이전트).

### Phase 3 — 배포·문서

- 버전 2.0.0, CHANGELOG, README 재작성(설치 2줄 유지, 스킬별 데모 입출력, 환경별 주의).
- 책 독자 호환: chapter 폴더는 유지하되 README에 "배포본은 skills/, 챕터는 스냅샷" 명시 유지.

---

## 5. 결정이 필요한 항목

| # | 결정 | 선택지 | 권장 |
|---|------|--------|------|
| D1 | content-research와 data-collector 통합 여부 | 통합 / 유지+엔진 공유 | 통합 |
| D2 | HWPX 기능을 독립 스킬로 분리할지 | 분리 / doc-automation 내 references | 분리(트리거 명확) |
| D3 | 대용량 샘플 자산 위치 | Release 자산 / chapter 폴더 / 실습 플러그인 | **v2 변경**: 실습 전용 플러그인(강의 프롬프트가 플러그인 안에서 샘플을 찾으므로) |
| D4 | narration-video Lite 모드 추가 여부 | 추가 / Full만 유지 | 추가 |
| D5 | 책 본문과의 정합성 유지 범위 | 프롬프트 호환 유지 / 자유 변경 | 책 실습 프롬프트(PROMPT.MD)가 계속 동작하도록 evals에 포함 |
| D6 | 원저작자 권리 처리 (v2) | 서면 허락 / 허락 범위만 사용·나머지 재작성 / 전면 재작성 | 서면 허락 우선. 불가하면 재작성. 사내·강의 배포 전 필수 |
| D7 | 플러그인 분할 (v2) | 단일 유지 / 업무·크리에이터·실습 3분할 | 3분할(§7.3) |
| D8 | generate-shorts 사내 제공 범위 (v2) | 전면 제공 / 자사 채널 영상만 / 제외 | 자사·권리 확보 영상만, 쿠키 추출 기본 비활성 |
| D9 | narration-video 사내 제공 (v2) | 기본 제공 / 선택 설치 / 제외 | Gemini가 사내 승인 AI가 아니면 선택 설치(Lite만 기본) |
| D10 | 저장소 위치 (v2) | 공개 GitHub / 사내 GitHub Enterprise + 강의용 공개 미러 | 사내 GHE가 정본, 강의용은 태그 단위 공개 미러 |
| D11 | 사용자 맞춤 수정 방식 (v2) | 스킬 복제(fork)만 안내 / 오버라이드 폴더 + 단계별 방법론 | 오버라이드 우선, 복제는 마지막 단계(§8) |

---

## 6. 부록 — 즉시 수정 가능한 소항목(Quick Wins)

- 모든 SKILL.md에서 `/mnt/user-data`, `/mnt/skills`, `/home/claude`, `present_files`, `~/Desktop`, `computer://` 제거 또는 조건부화.
- `content_analyzer.py`의 `claude-sonnet-4-20250514` 하드코딩과 API 재호출 제거.
- excel-automation matplotlib `DejaVu Sans` → 공통 폰트 모듈.
- doc-automation description에 HWPX·회사 템플릿·URL 입력 추가, 차트 단독 요청은 제외 명시.
- generate-shorts·narration-video `allowed-tools` 최소화.
- meeting-minutes 완료 후 홍보 문구 삭제, 질문 3개를 기본값 포함 1회 확인으로.
- content-repurpose 상단 "파일 찾지 마라" 지시 제거.
- [완료] `.gitignore`에 `docs/.pdca-snapshots/`, `docs/.pdca-status.json`, `docs/.bkit-memory.json` 추가, 해당 파일 삭제.
- [완료] marketplace.json owner/url을 humanist96로 갱신, README 설치 명령을 `humanist96/claude-skills`로 변경.
- [완료] 작성자 로컬 경로가 하드코딩된 1회성 스크립트 4종 삭제(skills/와 chapter02).
- plugin.json 신설.

---

## 7. 사내 전사 배포·외부 강의 관점 보완 (v2)

### 7.1 법무·라이선스·저작권 (Gate 0)

**현재 상태(확인값)**
- 루트 LICENSE 없음. GitHub 메타데이터 `licenseInfo: null`.
- humanist96/claude-skills는 GitHub상 fork로 표시된다(부모 저장소 존재).
- 커밋 이력 28건 중 23건이 원저작자 계정, 5건이 다른 기여자다.
- 2026-10-01 작업으로 파일 안의 원 저장소·원저작자 표기는 제거했다. 커밋 이력과 GitHub fork 연결은 그대로다.

**의미**
- 라이선스가 없는 저작물은 저작권자에게 모든 권리가 유보된다. 파일에서 이름을 지워도 권리 관계는 바뀌지 않는다. 오히려 출처 표기 없는 재배포는 분쟁 시 불리하다.
- 사내 전사 배포와 외부 강의(특히 유료)는 "복제·배포·2차적 저작물 작성"에 해당하므로 권한 근거가 필요하다.

**조치**
1. 원저작자로부터 사내 배포·강의 사용·수정에 대한 서면 허락을 받는다. 허락 범위에 맞춰 LICENSE(또는 사내 전용 고지)를 추가한다.
2. 허락을 받지 못하면 v2 재작성 범위를 "원본 코드·문구를 참조하지 않는 클린룸 재작성"으로 확정한다. 이 경우 Phase 1 규모가 커진다.
3. 커밋 이력에서 원저작자를 지우는 이력 재작성(force push)은 하지 않는다. 기여 기록을 지우는 것은 법적 근거 없이 위험을 키운다. fork 표시를 없애려면 GitHub 지원팀의 fork 분리 요청이나 새 저장소 이전을 쓰되, 권한 정리가 끝난 뒤에 한다.
4. 책 원고 성격의 파일(`chapter*/book-chapter-*.md`, `chapter08-content-repurpose/7_*_rewrite*.md`, `chapter12_*/부록*.pdf`)은 출판 계약상 권리 소재를 확인하고 외부 배포본에서 제외한다.

**제3자 저작물 점검**

| 자산 | 위치 | 판단 |
|------|------|------|
| FX 주간 전망 PDF | doc-automation 예제 1 | 금융기관 리서치로 보임. 재배포 권한 확인 전 사용 중지, 자체 제작 샘플로 교체 권장 |
| 팁스 지원계획 공고 hwpx | 예제 3 | 공공기관 공고. 공공누리 유형 확인 후 출처 표기 |
| 삼성전자 투자분석 pptx | 예제 2 | 생성 결과물. 투자 판단 오해 소지가 있어 강의용 문구 확인 |
| 공식 docx·pptx·xlsx 스킬 | 연계 대상 | source-available 라이선스. 코드 복사 금지, 절차 참조만 |
| kangdacool/hwpx-editing-skill 등 MIT 스킬 | 패턴 참조 | 코드를 가져오면 MIT 고지 포함 |

**스킬 기능상의 법적 리스크**
- **generate-shorts**: YouTube 다운로드, 브라우저 쿠키 추출(`YT_COOKIE_BROWSER`), User-Agent 변경을 "봇 감지 우회"로 문서화하고 있다. 기업 배포 시 플랫폼 약관 위반과 타인 영상 2차 저작물 문제가 생긴다. 사내판은 권리를 가진 영상(자사 채널, 로컬 파일)만 처리하도록 범위를 좁히고, 쿠키 추출은 기본 비활성, "우회" 표현은 삭제한다. 로컬 파일 입력 지원(§1.2 (7))을 이 이유로 우선순위를 올린다.
- **AI 생성물 표시**: narration-video·카드뉴스·리퍼포징 결과물을 대외 게시할 경우, 2026년 1월 시행된 「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」의 생성형 AI 결과물 고지 의무가 적용되는지 법무 검토를 받는다. 적용되면 스킬 출력 단계에 고지 문구·메타데이터 옵션을 넣는다.
- **data-collector**: 투자 조언 금지 규칙은 유지한다. 부동산·금융 보고서 하단 면책 문구를 표준화한다.

### 7.2 데이터 보호·보안

**스킬별 데이터 흐름**

| 스킬 | 다루는 데이터 | 외부로 나가는 경로 | 사내 기본 정책(제안) |
|------|---------------|--------------------|-----------------------|
| meeting-minutes | 회의 녹음·발언(인사·영업 정보 포함 가능) | 로컬 STT(faster-whisper)라 음성은 외부 전송 없음. 텍스트는 Claude로 전송 | 로컬 STT를 강점으로 명시. 외부 STT 기본 금지 |
| excel-automation | 고객명·전화·이메일 등 개인정보 | Claude로 전송 | 처리 전 개인정보 포함 여부 고지, 마스킹 옵션 |
| doc-automation | 내부 보고서·재무 수치 | Claude로 전송 | 문서 등급(대외비 이상) 처리 가이드 |
| data-collector / content-research | 검색어, 공개 웹 콘텐츠 | 웹검색·RSS·유료 API | 검색어에 내부 정보 금지 안내 |
| generate-shorts | 영상·자막 | YouTube | 권리 확보 영상만 |
| narration-video | 원고 텍스트 | **Google Gemini API** | 사내 승인 AI가 아니면 Full 모드 비활성 |
| content-repurpose | 원고 | Claude로 전송 | 일반 |

전제: Claude 사용 자체(Team/Enterprise 플랜, 데이터 보존 설정)는 회사 승인 범위를 따른다. 이 계획서는 그 위에 스킬이 추가로 여는 외부 경로만 다룬다.

**보안 항목**
- **프롬프트 인젝션**: 웹페이지·RSS·업로드 문서 안의 문장은 지시가 아니라 데이터라는 규칙을 data-collector·content-research·doc-automation 본문에 넣는다.
- **최소 권한**: `allowed-tools`의 무제한 `Bash`를 필요한 명령 패턴으로 좁힌다.
- **비밀 정보**: API 키는 `userConfig`(`sensitive: true`)로만 받는다. config 파일·로그 출력 금지를 CI에서 정규식으로 검사한다.
- **공급망**: 의존성 `==` 고정과 잠금 파일. `--break-system-packages` 대신 가상환경이나 `uv`. `curl | sh` 설치 안내는 사내 배포 문서에서 사내 소프트웨어 센터 경로로 대체. yt-dlp 자동 업그레이드 제거.
- **폐쇄망·프록시**: 사내 PyPI 미러, 프록시 환경 변수, 폰트 사전 배포 경로를 문서화한다.
- **보안 검토 산출물**: 스킬별 위협 요약 1쪽, 정보보호팀 승인 기록을 `docs/security/`에 둔다.

### 7.3 배포 구조·운영

**플러그인 3분할** (한 마켓플레이스, 세 플러그인)

| 플러그인 | 포함 | 대상 | 기본 설치 |
|----------|------|------|-----------|
| `kevin-skills-book` (업무) | doc-automation, excel-automation, meeting-minutes, data-collector, hwpx-editor(분리 시) | 전 직원, 수강생 | 사내 기본 |
| `kevin-skills-creator` (크리에이터) | content-research, content-repurpose, generate-shorts, narration-video | 마케팅·홍보, 수강생 | 선택 |
| `kevin-skills-practice` (실습) | 실습 샘플·정답 예시·실습 프롬프트, 사전 점검 스킬 | 강의 수강생 | 강의 시에만 |

- (2026-10-02 변경) 처음에는 업무 플러그인 이름을 기존 `claude-skills-book`으로 유지해 책 독자의 설치 명령을 지키려 했다. 그러나 최신 Claude Code CLI가 `claude-`로 시작하는 플러그인 이름을 Anthropic 예약어로 거부하고, `kevin-claude-skills-book`처럼 `claude-skills`를 포함한 이름도 공식 플러그인처럼 읽힌다고 경고해(`--strict`에서 실패), 마켓플레이스는 `kevin-claude-skills`, 플러그인은 `kevin-skills-book`·`-creator`·`-practice`로 바꿨다. 책 독자의 v1.6.1 설치 명령은 더 이상 동작하지 않으므로 README와 CHANGELOG에 새 명령을 안내한다.
- 실습 프롬프트 2-2·2-5("플러그인 안의 샘플을 찾아 복사")는 실습 플러그인에서 동작하도록 문구를 "실습 플러그인"으로 갱신한다. eval에 포함해 회귀를 막는다.

**하위 호환·폐기 정책**
- 스킬을 통합·개명할 때 기존 이름의 스텁 스킬을 한 개 메이저 버전 동안 유지한다. 스텁은 새 스킬로 안내만 한다.
- 폐기 예정 기능은 CHANGELOG와 스킬 본문 첫 줄에 표기한다.

**릴리스 채널·버전 고정**
- semver를 쓴다. 스킬 동작 변경은 minor, 이름·입출력 변경은 major.
- `stable`(태그) / `main`(개발) 2채널. 마켓플레이스 entry의 GitHub source에 `ref`(태그)와 `sha`를 고정해 강의 회차별로 동일 버전을 보장한다.
- 강의 회차마다 "강의용 태그"를 만들고 교안에 그 태그를 적는다.

**사내 배포 메커니즘**
- 정본 저장소를 사내 GitHub Enterprise에 두고 강의용은 태그 단위로 공개 미러에 푸시한다.
- Claude Code 관리형 설정으로 사내 마켓플레이스를 기본 등록하고, 허용 마켓플레이스를 제한한다. Cowork·Team/Enterprise 관리자 콘솔의 조직 단위 플러그인 배포 기능 지원 범위는 착수 시점에 공식 문서로 확인한다.
- narration-video의 stdio MCP 서버가 Cowork·claude.ai에서 동작하는지 착수 전에 실측한다. 미지원이면 Lite 모드만 해당 환경에 노출한다.

**공존 플러그인과의 충돌**
- 사내 PC에는 공식 docx·pptx·xlsx·pdf 스킬과 업무별 플러그인이 함께 설치된다. 트리거 평가 세트에 "공식 xlsx 스킬이 맡아야 할 요청"(단순 셀 편집, 수식 추가)을 near-miss 음성 사례로 넣는다.
- 공식 스킬이 설치된 환경과 없는 환경 두 가지로 eval을 돌린다.

**표면별 지원 매트릭스** (README와 각 스킬 `compatibility`에 명시)

| 스킬 | Claude Code Win | Claude Code Mac | Cowork | claude.ai |
|------|:-:|:-:|:-:|:-:|
| doc-automation | 지원 | 지원 | 지원 | 지원(업로드 시 vendoring 필요) |
| excel-automation | 지원 | 지원 | 지원 | 지원 |
| meeting-minutes | 지원 | 지원 | 확인 필요(STT 시간 제한) | 확인 필요 |
| data-collector | 지원 | 지원 | 지원 | 지원 |
| generate-shorts | 확인 필요(폰트·경로) | 지원 | 지원(분할 실행) | 확인 필요(네트워크) |
| narration-video | 확인 필요 | 지원 | 확인 필요(MCP) | 미지원 예상 |

"확인 필요" 칸은 Phase 0의 스모크 테스트로 채운다.

**지원 체계**
- 저장소 이슈 템플릿(버그·요청·트리거 오작동), 사내 문의 채널, 담당자 지정.
- `/skill-doctor`로 스킬별 컨텍스트 비용·미사용 스킬을 분기마다 점검해 정리 대상을 고른다.

### 7.4 강의 운영

- **사전 점검 스킬**(`doctor`, 실습 플러그인): Python·ffmpeg·한글 폰트·네트워크·필수 패키지·플러그인 버전을 확인하고 실패 항목별 해결 명령을 출력한다. 강의 전날 수강생이 실행한다.
- **오프라인 데모 모드**: 수강생이 같은 IP로 YouTube·Gemini·웹검색을 동시에 호출하면 차단·레이트리밋이 난다. generate-shorts는 이미 동봉된 자막·하이라이트 결과(`assets/output/transcript.json` 등)로 Phase 2b부터 진행하는 경로를, data-collector는 미리 수집한 `collected_data.json`으로 분석부터 진행하는 경로를 공식화한다.
- **환경 다양성**: 국내 기업 수강생은 Windows 비중이 높다. Windows 스모크 테스트를 강의 전 필수로 한다.
- **수강 요건 표**: 필요한 Claude 플랜, Cowork 사용 가능 여부, 설치 권한(관리자 권한 없는 사내 PC), 예상 디스크 사용량.
- **결과 편차 안내**: LLM 결과는 매번 다르다. 교안 스크린샷과 다를 수 있음을 알리고, 평가 기준(품질 게이트 통과 여부)으로 실습 성공을 판단하게 한다.
- **강사 가이드**: 실습별 소요 시간, 흔한 실패와 복구 명령, 대체 실습.

### 7.5 평가 체계의 현실성 보정

- **비용 추정**: 8개 스킬 × 케이스 4개 × 3회 × 2(유/무) ≈ 192회 실행. 영상 스킬은 회당 수 분이 걸린다. `tags`로 `smoke`(PR마다, 저비용)와 `full`(릴리스 전)을 나누고 `--max-cost-usd`로 상한을 둔다.
- **모델 범위**: 사내 사용자 기본 모델과 강의 수강생 플랜의 기본 모델로 평가한다. 공식 체크리스트대로 Haiku·Sonnet·Opus 계열을 최소 1회씩 돌린다.
- **한국어 트리거 평가**: 반말·존댓말·오타·영문 혼용("엑셀 정리 ㄱㄱ", "회의록 좀")을 포함한다.
- **Windows 검증**: `claude plugin eval`은 Windows 네이티브 샌드박스가 없어 CI는 Linux에서 돈다. Windows 고유 문제(폰트 경로, 백슬래시, ffmpeg 이스케이프)는 릴리스 전 수동 Windows 매트릭스로 확인한다.
- **CI 비밀 정보**: eval 실행용 API 키는 저장소 Secrets에만 둔다. 포크 PR에서는 eval을 돌리지 않는다.

### 7.6 성공 기준·일정·담당·리스크

**스킬별 완료 정의(Definition of Done)**

| 항목 | 기준 |
|------|------|
| 정적 검사 | `validate_skills.py`, `claude plugin validate --strict` 통과 |
| 기능 평가 | `claude plugin eval` 점수 0.8 이상, baseline 대비 Δ > 0 |
| 트리거 | 트리거 평가 세트 정확도 90% 이상(교차 플러그인 near-miss 포함) |
| 책·강의 호환 | 해당 장 실습 프롬프트 전부 통과 |
| 크로스플랫폼 | 지원 매트릭스의 "지원" 칸 스모크 통과 |
| 문서 | README 데모, CHANGELOG, 보안 1쪽 요약 |
| 커스터마이즈 | README에 확장 지점 표, 오버라이드 예제 1개 이상, 오버라이드 적용 eval 1건 통과(§8) |

**배포 KPI**: 설치부터 첫 성공까지 10분 이내(강의), 월간 활성 사용자·스킬별 호출 수(사내, 수집 가능 범위에서), 이슈 처리 리드타임.

**마일스톤(초안, 규모 기반 상대 일정)**

| 단계 | 산출물 | 상대 기간 |
|------|--------|-----------|
| Gate 0 | 권리 확인, 보안 검토, 분할 구조 결정 | 외부 의존(법무·원저작자 회신)에 따라 변동 |
| Phase 0 | 공통 기반, CI, 사전 점검 | 1~2주 |
| Phase 1 업무 4종 | 업무 플러그인 v2.0.0 | 스킬당 1주 내외 |
| 사내 파일럿 | 1~2개 부서 시범 운영, 피드백 반영 | 2주 |
| Phase 1 크리에이터 4종 | 크리에이터 플러그인 | 스킬당 1~1.5주 |
| 강의 리허설 | 강의용 태그, 강사 가이드, 오프라인 모드 | 1주 |

**역할(RACI 초안)**: 플러그인 오너(최종 책임), 스킬 담당자(구현), 정보보호팀(보안 승인), 법무(권리·AI 고지), 파일럿 부서(검증), 강사(교안·리허설).

**리스크 등록부**

| 리스크 | 가능성 | 영향 | 대응 |
|--------|:-----:|:----:|------|
| 원저작자 허락 불가 | 중 | 높음 | 클린룸 재작성으로 전환, 일정 재산정 |
| 공식 스킬·Claude Code 사양 변경 | 높음 | 중 | 버전 고정, 월 1회 공식 문서 점검, eval 회귀 |
| Gemini 모델 폐기 | 높음 | 중 | 모델 ID 단일 출처화, Lite 모드 |
| YouTube 차단·약관 이슈 | 높음 | 중 | 로컬 파일 입력, 오프라인 데모 |
| 사내 보안 심사 지연 | 중 | 높음 | 업무 플러그인부터 단계 공개 |
| 강의장 네트워크 장애 | 중 | 높음 | 오프라인 모드, 사전 점검 |
| 트리거 충돌로 엉뚱한 스킬 실행 | 중 | 중 | 교차 플러그인 트리거 평가 |

**롤백**: 문제 발생 시 마켓플레이스 `ref`를 직전 stable 태그로 되돌린다. 사용자는 플러그인 업데이트만으로 복구된다.

### 7.7 v1 정오표

| v1 위치 | 오류·빈틈 | 수정 |
|---------|-----------|------|
| §3.2 공통 스크립트 | `_shared` 런타임 참조가 수동 설치·claude.ai 업로드에서 깨짐 | vendoring 빌드 단계 추가 |
| §3.3, D3 | 샘플 제거가 강의 실습 프롬프트를 깨뜨림 | 실습 플러그인으로 이동 |
| §3.3 | "owner를 humanist96로, 원 저장소는 README에 출처로" | owner 변경은 완료. 출처 표기 여부는 §7.1 권리 정리 결과에 따름 |
| §0 표 6행 | 바이너리 크기 근거 불명확 | 실측 반영(skills/ 약 23MB, docx 6개 17.7MB) |
| §3.5 | description 원칙 두 가지를 상충한 채 병기 | 형식 통일 |
| §2.1 5번, §3.5 | "절대 규칙"을 일괄 완화하면 안전 규칙도 약화 | 안전 규칙 목록은 강제 유지 |
| §1.2 (5) | content-research 통합 시 호환 계획 없음 | 스텁 스킬·폐기 정책 |
| §3.4 | 평가 비용·모델 범위·한국어·Windows 고려 없음 | §7.5 |
| 전체 | 법무·보안·운영·강의 관점 부재 | §7.1~7.4 |
| 전체 | 사용자가 스킬을 맞춤 수정하는 경로·방법론 부재 | §8 |

---

## 진행 현황

### Phase 0 — 2026-10-01 (v2 브랜치, 미커밋)

권장안(D1~D11)대로 진행했다. 결과 증거는 저장소 루트 `GATES.md`에 있다.

| 항목 | 결과 |
|------|------|
| 플러그인 3분할 | `plugins/kevin-skills-book`(업무 4), `plugins/kevin-skills-creator`(콘텐츠·영상 4), `plugins/kevin-skills-practice`(practice-samples, doctor 신규). `claude plugin validate --strict` 통과 |
| 마이그레이션 | v1.6.1 파일 119개 전부 추적: 동일 105, 의도 수정 3, 글꼴 제거 6, 의도 삭제·이동 5 |
| 슬림화 | 업무 플러그인 약 20MB → 0.4MB. 예제 docx 내장 글꼴 제거(12개 35MB → 99KB, 본문 텍스트 동일) |
| 공통 모듈 | `shared/`(env, fonts, paths, overrides, validate_overrides, doctor + 규약 문서 2종) → 스킬 9개에 vendoring 90개 파일 |
| 검증·CI | 정적 검증기(baseline 37건 동결, 양성 대조 통과), 단위 테스트 37개, eval 골격 10케이스, GitHub Actions(Windows·Ubuntu) |
| 의존성 | requirements 5개 고정(yt-dlp 예외), `constraints.txt` 78개, 깨끗한 venv 동시 설치·import 검증 |
| 오버라이드 | 폴더 규약 `.claude/claude-skills/<스킬명>/`, 보호 규칙 5개, 검사 스크립트 |
| baseline | `v1.6.1` 태그, `tools/make_baseline.py`로 재현 |

Phase 0 중 새로 발견해 고친 결함
- 한국어 Windows에서 pip가 requirements를 cp949로 읽어, UTF-8 한글 주석이 있으면 설치가 실패한다 → requirements·constraints를 ASCII로 제한하고 검사 규칙 추가.
- core.autocrlf 환경에서 `.sh`가 CRLF로 체크아웃돼 bash가 실패한다 → `.gitattributes`로 LF 고정.
- doctor가 같은 패키지를 필수/선택으로 쓰는 스킬을 같은 판정으로 묶던 오류 → 스킬별 판정으로 수정, 회귀 테스트 추가.

남은 항목
- `claude plugin eval` 실제 실행: 이 계정에서 early access라 실행 불가(GATES.md G9 handoff).
- Gate 0 사용자 조치 9건: `docs/gate0-handoff.md`.

### Phase 1 — doc-automation(+hwpx-editor 분리) — 2026-10-01 (v2 브랜치, 미커밋)

증거: `GATES.p1-doc-automation.md`, 분석: `docs/03-analysis/doc-automation-phase1.analysis.md`

| 항목 | 결과 |
|------|------|
| 재설계 | 스토리라인 중심 워크플로, extract_sources·build_deck·verify_deck·render_slides 신설 |
| 분리 | hwpx-editor(D2 권장안) — 텍스트 노드 한정 치환, plan·verify, 미리보기 갱신 |
| 비교 평가 | v1.6.1 대비 기대 항목 통과율 0.79 → 1.00(4 eval, 각 1회), 시간 340초 → 281초 |
| hwpx 평가 | 책 실습 2-6·2-7 모두 통과 |
| 평가 중 발견·수정 | 11건(분석 문서 §3) |
| 트리거 | 실측은 CLI 로그인 만료로 handoff(H10). 대리 라우팅 10/10, 오발동 0 |
| 회귀 | `tools/run_regression.py` 21개 검사 통과 |

### Phase 1 — excel-automation — 2026-10-01 (v2 브랜치, 미커밋)

증거: `GATES.p1-excel-automation.md`, 분석: `docs/03-analysis/excel-automation-phase1.analysis.md`

| 항목 | 결과 |
|------|------|
| 재설계 | excel_profile·clean_data·analysis_tools·consolidate·recalc·verify_excel 신설, SKILL.md 399줄 → 165줄 + references 3개 |
| 실습 파일 | v1.6.1 '실습 입력'이 처리된 결과물이었음 → 진짜 원본 3종 + 정답표 생성(재현 가능), 옛 파일은 완성 예시로 |
| 비교 평가 | v1.6.1 대비 기대 항목 통과율 0.93 → 1.00(3 eval, 각 1회), 시간 245초 → 148초, 토큰 14.3만 → 12.9만 |
| 검증 장치 | verify_excel 결함 20종 양성 대조, 정답표 대조 테스트 3종, 채점기 대조 |
| 평가 중 발견·수정 | 6건(분석 문서 §3) |
| 트리거 | 측정 안 함(트리거 세트 없음, CLI 로그인 필요 — H10) |
| 회귀 | `tools/run_regression.py` 25개 검사 통과 |

### Phase 1 — meeting-minutes — 2026-10-02 (v2 브랜치, 미커밋)

증거: `GATES.p1-meeting-minutes.md`, 분석: `docs/03-analysis/meeting-minutes-phase1.analysis.md`

| 항목 | 결과 |
|------|------|
| 재설계 | transcribe(재작성)·prepare_transcript·build_minutes·verify_minutes, minutes.json 근거 구조. SKILL.md 221줄 → 약 140줄 + references 3개 |
| 계획서 문제 해소 | 컨테이너 경로 제거, 질문 3개 필수 → 기본값 1회 확인, 홍보 문구 삭제, 한국어 small 기본, 할 일 '미정' 규칙, docx 조건부 연계 |
| 실습 | 클로바노트 녹취록 추가, 녹음 3개·녹취록 정답표(STT 함정·불확실 항목 포함) |
| 비교 평가 | iteration-1 0.952 대 0.975(v1.6.1 우세, 게이트 실패) → 인식 힌트 기본값·기준 수치 누락 수정 → iteration-2 0.977 대 0.975(사실상 동률). 시간은 v2 327초 대 270초(남은 백그라운드 작업 포함, 산출물 완성 기준 237초) |
| 점수 밖 차이 | v1.6.1은 음성 실행 6/6 STT 오류 우회 필요, 최종 응답 홍보 문구 8/8. v2는 0/8 |
| 평가 중 발견·수정 | 8건(분석 문서 §4), 정답표 가격 수정 1건(§3, 편향 방지 처리) |
| 회귀 | `tools/run_regression.py` 30개 검사 |

### Phase 1 — content-repurpose — 2026-10-02 (v2 브랜치, 미커밋)

증거: `GATES.p1-content-repurpose.md`, 분석: `docs/03-analysis/content-repurpose-phase1.analysis.md`

| 항목 | 결과 |
|------|------|
| 재설계 | brief.json(핵심 메시지·숫자·단서) → 선택한 플랫폼 스펙만 읽기 → count_chars·check_repurpose 검사. SKILL.md 2,301단어 → 133줄 + 플랫폼 스펙 14개·훅·감사 절차 |
| 계획서 문제 해소 | "외부 파일 찾지 마라" 지시 삭제, Cowork 경로·링크 형식 제거, 질문 필수 → 기본값 1회 확인, 감사·갭 집계는 content_inventory.py |
| 실습 | 제3자 유튜브 녹취 대신 자체 작성 원본 대본, 정답표(숫자 13개·핵심 메시지·단서, 책 8-1·8-2 집계 정답) |
| 비교 평가 | iteration-1(4개 eval) 1.00 대 1.00, iteration-2(사전 위험 근거 eval 2개 추가, 6개) 1.00 대 1.00. 천장 효과로 판별 불가 → R8 포기(ABANDON), H12로 이관. 시간 138초 대 147초, 토큰 13.2만 대 12.4만 |
| 점수 밖 차이 | v1.6.1 예시 파일의 지어낸 숫자 4개(30%·0%·2시간·4시간)와 틀린 계산식을 검증기가 검출. v2 예시는 통과 |
| 평가 중 발견·수정 | 채점기 오판 6건(v1.6.1 쪽 불리), 스킬 결함 9건(분석 문서 §3·§4) |
| 회귀 | `tools/run_regression.py` 34개 검사 통과 |

다음 스킬: data-collector (로드맵 순서 5)

---

## 8. 사용자 맞춤 고도화 설계와 방법론 (v2)

### 8.1 문제와 목표

현재 사용자가 스킬을 자기 업무에 맞추려면 플러그인 설치 폴더 안의 SKILL.md나 스크립트를 직접 고쳐야 한다. 이 방식에는 세 가지 문제가 있다.

- 플러그인을 업데이트하면 설치 폴더가 새 버전으로 바뀌어 수정 내용이 사라진다.
- 원본과 수정본이 같은 이름으로 공존하면 어느 스킬이 트리거될지 예측할 수 없다.
- 무엇을 어디까지 고쳐도 되는지 기준이 없어 안전 규칙까지 지워질 수 있다.

목표는 **"대부분의 맞춤은 스킬 코드를 건드리지 않고, 업데이트 후에도 유지되며, 팀과 공유할 수 있게"** 하는 것이다. 이를 위해 스킬 쪽에는 확장 지점을 설계하고, 사용자 쪽에는 단계별 방법론과 도우미 스킬을 제공한다.

### 8.2 설계 — 맞춤 수준 5단계와 확장 지점 계약

수준이 낮을수록 쉽고 업데이트에 안전하다. 사용자는 항상 가장 낮은 수준부터 시도한다.

| 수준 | 무엇을 바꾸나 | 방법 | 업데이트 후 유지 | 필요 역량 |
|:---:|---------------|------|:---:|-----------|
| L0 설정 | 기본 출력 폴더, 회사명, 기본 역할, 보고 톤, 언어 | 플러그인 `userConfig`(설치 시 입력) 또는 설정 파일의 값 | 유지 | 없음 |
| L1 자산 교체 | 회사 PPT 템플릿, HWPX 결재 양식, 이메일 템플릿, 브랜드 보이스, 용어집·참석자 사전 | 오버라이드 폴더에 같은 이름 파일 배치 | 유지 | 파일 다루기 |
| L2 지식 추가 | 도메인 프로필, 플랫폼 스펙, 회의록 양식, 분석 관점, 금칙어 | 오버라이드 폴더에 references 파일 추가 | 유지 | 마크다운·YAML 작성 |
| L3 스킬 복제 | 워크플로 자체(단계 추가·삭제, 다른 출력 형식) | 스킬을 새 이름으로 복제해 개인·팀 스킬로 운영, 원본은 끔 | 유지(원본 개선은 직접 병합) | 스킬 구조 이해 |
| L4 신규 스킬 | 기존 스킬로 표현할 수 없는 업무 | skill-creator로 새로 작성 | 해당 없음 | 스킬 작성 |

**오버라이드 탐색 규약** (모든 스킬 공통, `_shared/references/overrides.md`에 정의)

스킬은 확장 지점 파일을 다음 순서로 찾고, 먼저 발견된 것을 쓴다.

1. 프로젝트 폴더: `<작업폴더>/.claude/claude-skills/<스킬명>/` — 팀이 Git으로 공유
2. 사용자 폴더: `~/.claude/claude-skills/<스킬명>/` — 개인 기본값

(플러그인이 3개로 나뉘므로 폴더 이름은 플러그인명이 아닌 공통 `claude-skills`를 쓴다. Phase 0에서 확정.)
3. 스킬 기본값: 플러그인 안의 `assets/`·`references/`

- 설정 값은 같은 폴더의 `settings.yaml`에 둔다. 단순 값은 플러그인 `userConfig`로도 받을 수 있다. 공식 plugin-dev의 `.claude/<plugin>.local.md` 설정 패턴과 호환되게 설계한다.
- 오버라이드 폴더는 사용자에게 보이는 위치여야 한다. `${CLAUDE_PLUGIN_DATA}`는 업데이트에는 안전하지만 숨은 폴더라 사용자가 편집하기 어려우므로 캐시 용도로만 쓴다.
- 스킬은 실행 시작 시 "적용된 오버라이드 목록"을 한 줄로 알려 준다. 사용자가 맞춤이 실제로 반영됐는지 확인할 수 있어야 한다.
- 이 탐색이 모델 지시만으로 안정적으로 동작하는지는 eval로 검증한다. 불안정하면 `_vendor/overrides.py`가 경로를 해석해 결과를 출력하고 스킬은 그 출력만 따른다.

**확장 지점 계약**
- 각 스킬 README에 "커스터마이즈 포인트" 표를 둔다. 항목은 파일명, 형식, 기본값 위치, 예시다.
- 이 표는 공개 인터페이스로 취급한다. 형식을 바꾸면 major 버전을 올리고 마이그레이션 안내를 낸다.
- 오버라이드로도 바꿀 수 없는 **보호 규칙**을 명시한다: 원본 덮어쓰기 금지, 비밀 정보 파일 기록 금지, 투자 권유 금지, 개인정보 외부 전송 전 확인, 이상값 자동 수정 금지. 오버라이드 파일이 이 규칙과 충돌하면 스킬은 보호 규칙을 따르고 그 사실을 알린다.

**스킬별 확장 지점(초안)**

| 스킬 | L0 설정 | L1 자산 | L2 지식 |
|------|---------|---------|---------|
| doc-automation | 기본 슬라이드 수, 보고 대상(팀장·임원), 회사명 | 회사 PPT 템플릿, 브랜드 색·폰트, HWPX 결재 양식, 이메일 템플릿 | 보고서 스토리라인(주간·월간·투자 검토), 부서 용어집 |
| excel-automation | 날짜·전화번호 표기 형식, 출력 파일명 규칙 | 결과 시트 서식 템플릿 | 이상값 판정 기준, 업종별 분석 관점, 키 컬럼 후보 사전 |
| meeting-minutes | 기본 역할·용도·출력 형식(질문 생략용), STT 모델 | 부서 회의록 양식(docx·md) | 참석자·용어 사전, 회의 유형별 템플릿(주간회의·고객미팅·면접) |
| data-collector | 기본 깊이, 보고서 언어 | 보고서 템플릿, 면책 문구 | 도메인 프로필 추가(예: 2차전지, 물류), 신뢰 소스 목록 |
| content-research | 기본 용도, 언어 | 브리핑 템플릿 | RSS·검색 소스 목록, 용도별 분석 관점 |
| content-repurpose | 기본 플랫폼 묶음, 톤 | 브랜드 보이스, 해시태그 정책 | 플랫폼 스펙 추가(사내 뉴스레터·블라인드 등), 금칙어, 우수 예시 |
| generate-shorts | 기본 레이아웃·쇼츠 수 | 폰트, 후크 스타일, 카드뉴스 테마 | 훅 문구 사례집, 채널 보이스 |
| narration-video | 기본 스타일·음성·BGM 볼륨 | 배경 이미지 세트(Lite) | 콘텐츠 유형 프리셋 |

### 8.3 사용자 방법론 — "맞춤 고도화 6단계"

공식 skill-creator의 평가 루프를 비개발자도 따라 할 수 있게 줄인 절차다. 사내 가이드와 강의 모듈의 뼈대로 쓴다.

1. **불만 수집**: 스킬 결과물에서 바꾸고 싶은 점을 실제 사례 3개로 적는다. "더 좋게"가 아니라 "임원 보고서인데 결론이 마지막 장에 있다"처럼 구체적으로 쓴다.
2. **수준 판단**: 아래 판단 순서로 가장 낮은 수준을 고른다.
   - 값 하나만 바꾸면 되는가 → L0
   - 우리 회사 양식·템플릿·용어로 바꾸면 되는가 → L1
   - 스킬이 모르는 우리 업무 지식을 알려 주면 되는가 → L2
   - 작업 순서나 결과물 종류 자체가 달라야 하는가 → L3
   - 기존 스킬과 목적이 다른가 → L4
3. **테스트 요청 작성**: 1단계 사례를 실제 요청 문장 2~3개와 "합격 기준" 체크리스트로 바꾼다. 예: "결론이 2번째 슬라이드에 있다", "회사 로고가 표지에 있다".
4. **수정**: 도우미 스킬(§8.4)로 오버라이드 파일을 만들거나, L3·L4는 skill-creator로 작업한다.
5. **전후 비교**: 같은 요청을 수정 전후로 실행해 합격 기준으로 비교한다. 여유가 있으면 skill-creator의 비교 뷰어를 쓴다(Cowork에서는 정적 HTML 출력). 기준을 못 넘으면 3단계로 돌아간다.
6. **공유·반영**: 팀 공용이면 프로젝트 오버라이드 폴더를 Git에 올린다. 여러 팀에 유용하면 본체 개선 요청을 낸다(§8.5).

**L3 스킬 복제 시 지켜야 할 규칙**
- 새 이름을 쓴다(예: `doc-automation-finance`). 같은 이름이면 원본과 충돌한다.
- 원본 스킬은 설정의 스킬 오버라이드로 끄거나 이름만 노출되게 한다. 둘 다 켜 두면 트리거가 분산된다.
- description에 원본과 무엇이 다른지, 언제 원본 대신 쓰는지를 적는다.
- 복제본 상단에 기반 버전(예: `based-on: kevin-skills-book 2.1.0`)을 기록해 원본 업데이트 시 비교할 수 있게 한다.
- 복제본에서도 보호 규칙은 그대로 유지한다.

### 8.4 제공할 도구

| 도구 | 위치 | 역할 |
|------|------|------|
| `customize` 도우미 스킬 | 업무 플러그인, `disable-model-invocation: true`로 `/kevin-skills-book:customize`에서만 실행 | 6단계 방법론을 대화로 진행한다. 불만 사례를 묻고, 수준을 판단하고, 오버라이드 폴더·파일 골격을 만들고, 검증을 실행한다 |
| 오버라이드 검증 스크립트 | `_shared` → 각 스킬 `_vendor` | 오버라이드 파일 형식, 필수 필드, 보호 규칙 충돌, 비밀 정보 포함 여부를 검사한다 |
| 확장 지점 예제 | 실습 플러그인 | 회사 PPT 템플릿 적용, 부서 회의록 양식, data-collector 도메인 프로필 추가의 완성 예시 |
| 개인 평가 케이스 템플릿 | 실습 플러그인 | 사용자가 만든 테스트 요청을 `claude plugin eval --eval-dir`로 돌릴 수 있는 골격 |
| 외부 도구 연계 | 문서 안내 | 공식 skill-creator(작성·평가·description 최적화), Cowork용 plugin customizer(조직별 플러그인 맞춤)는 재구현하지 않고 안내만 한다 |

### 8.5 거버넌스 — 개인 맞춤에서 전사 개선으로

- **세 단계 범위**: 개인(사용자 폴더) → 팀(프로젝트 폴더, 팀 저장소) → 전사(본체 반영). 범위가 넓어질수록 검증 기준을 올린다.
- **본체 반영 경로**: 두 개 이상 팀이 같은 맞춤을 쓰면 본체 기본값이나 공식 확장 지점으로 승격을 검토한다. `CONTRIBUTING.md`에 요청 양식(사례, 합격 기준, 오버라이드 파일)을 둔다.
- **보안 경계**: 외부 API 추가, 네트워크 접근 확대, `allowed-tools` 확대는 개인·팀 맞춤에서 허용하지 않고 본체 개선 요청으로만 받는다. 보안 검토(§7.2)를 거친다.
- **호환성 공지**: 확장 지점 형식 변경은 major 버전과 함께 공지하고, 오버라이드 검증 스크립트가 구형식을 감지해 안내한다.

### 8.6 문서·교육 산출물

- `docs/customization-guide.md`: 사용자용 가이드. 5단계 수준표, 판단 순서, 6단계 방법론, 스킬별 확장 지점, 자주 묻는 질문.
- 각 스킬 README의 "커스터마이즈 포인트" 섹션.
- 강의 모듈: 책 5장 "다른 사람이 만든 스킬 개선하기"가 현재 "작성 예정"이므로 이 방법론을 그 내용으로 채운다. 실습은 "회사 PPT 템플릿을 L1로 적용 → 결과 비교 → 팀 공유" 1시간 구성.
- 사내 파일럿 부서에서 실제 맞춤 사례 3건 이상을 수집해 가이드 예시로 싣는다.

### 8.7 로드맵 반영

| 단계 | 커스터마이즈 관련 작업 |
|------|-------------------------|
| Phase 0 | 오버라이드 탐색 규약, 보호 규칙 목록, 검증 스크립트 골격 |
| Phase 1(스킬별) | 확장 지점 구현, README 표, 오버라이드 적용 eval 1건 |
| Phase 2 | `customize` 도우미 스킬, 예제·개인 eval 템플릿 |
| Phase 3 | 사용자 가이드, 강의 모듈, CONTRIBUTING.md |
