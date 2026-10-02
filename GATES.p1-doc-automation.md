# Gates: Phase 1 — doc-automation 고도화 + hwpx-editor 분리 (계획서 §1.2(1), §4 Phase 1, D2)

OWNS: plugins/kevin-skills-book/skills/doc-automation/**, plugins/kevin-skills-book/skills/hwpx-editor/**, plugins/kevin-skills-book/evals/**, plugins/kevin-skills-practice/skills/practice-samples/samples/catalog.json, shared/optional/**, shared/scripts/doctor.py, tools/**, tests/**, .github/workflows/ci.yml, docs/01-plan/skills-upgrade.plan.md, CHANGELOG.md, README.md, GATES.p1-doc-automation.md, .workspace/**

Scope: doc-automation을 "입력 이해 → 보고 스토리라인 설계 → 렌더링 → 숫자 출처 검증"으로 재설계하고, HWPX 양식 편집을 hwpx-editor로 분리하며, v1.6.1 대비 평가에서 더 나은 결과를 증거로 남긴다.

- [x] P0: this ledger states outcomes that can fail
  CHECK: node C:/Users/Admin/.claude/skills/unlazy/scripts/gate-lint.mjs GATES.p1-doc-automation.md
  EXPECT: LINT OK
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:09:29.195Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=defe74e6fbb143ad1decbb94015fd56ab5ddacd58862c4e3b48233b85e6886ce; output-bytes=363

- [x] P1: 여러 형식의 실습 입력(pdf·docx·hwpx·png·csv·pptx)을 출처 ID가 붙은 source 묶음으로 추출한다
  CHECK: python tests/check_extract_sources.py
  EXPECT: EXTRACT OK
  DEPS: tests/check_extract_sources.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:09:34.790Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=f979adcafe69dff123020c938ecfa138eeed4fed91bd74a354530af51250ee65; output-bytes=92

- [x] P2: 슬라이드 유형 8종 outline이 편집 가능한 네이티브 차트·표를 포함한 pptx로 렌더링되고, 4:3 회사 템플릿의 크기·레이아웃을 따르며 템플릿 샘플 슬라이드가 남지 않는다
  CHECK: python tests/check_build_deck.py
  EXPECT: BUILD DECK OK
  DEPS: tests/check_build_deck.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:09:39.530Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=20b01edbb0f446a5f3fb29e7f416b0924572e1d265fc0c9b97c4af284e1acf85; output-bytes=147

- [x] P3: verify_deck가 출처에 없는 숫자를 잡아내고(양성 대조), 출처·파생 선언이 있는 깨끗한 덱은 통과시킨다
  CHECK: python tests/check_verify_deck.py
  EXPECT: VERIFY DECK CONTROL OK
  DEPS: tests/check_verify_deck.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:09:49.765Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=4edc7c4c88d187bcc7030599c0354cefdfcac72859d9bf5cc8370ba3a0ce3b9d; output-bytes=89

- [x] P4: hwpx-editor가 실습 결재문서의 텍스트만 바꾸고 나머지 ZIP 엔트리를 바이트 그대로 보존하며, 손상된 출력은 verify_hwpx가 잡아낸다
  CHECK: python tests/check_hwpx_editor.py
  EXPECT: HWPX EDITOR OK
  DEPS: tests/check_hwpx_editor.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:09:50.613Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=a680cd4529b4d606ed41d6f6c227d614d30142e7896bd4a7a02029f2f5525af5; output-bytes=467

- [x] P5: doc-automation과 hwpx-editor의 SKILL.md·README가 품질 규약(템플릿 섹션, description 경계, 500줄, 참조 파일 존재, 커스터마이즈 포인트, 환경 전용 경로 0건)을 충족한다
  CHECK: python tools/check_skill_quality.py doc-automation hwpx-editor
  EXPECT: SKILL QUALITY OK
  DEPS: tools/check_skill_quality.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:09:51.107Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=7e160c56baaca819fc7836e48ce8695ac435df3801e8be2e76c9825fde37614c; output-bytes=56

- [x] P6: Phase 0 회귀 없음 — 플러그인 검증·vendoring·정적 검증·마이그레이션·eval 구조·문서·크기·컴파일·단위 테스트가 모두 통과한다
  CHECK: python tools/run_regression.py
  EXPECT: REGRESSION OK
  DEPS: tools/run_regression.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:10:38.728Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=d8f6b30df88cc5c86f301c0cff8c5644be2610e93ee1a06673085bb7735bf01a; output-bytes=825

- [x] P7: skill-creator 형식 evals.json이 두 스킬에 있고 책 실습 프롬프트(2-3, 2-6, 2-7)를 포함하며 각 eval에 검증 가능한 expectations가 있다
  CHECK: python tools/check_skillcreator_evals.py doc-automation hwpx-editor
  EXPECT: SKILLCREATOR EVALS OK
  DEPS: tools/check_skillcreator_evals.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:10:39.170Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=12a4f25404ab11898864fd733a316e964450f840f51f01d6ff1d8b0fedaf084b; output-bytes=86

- [x] P8: 새 doc-automation이 v1.6.1 대비 benchmark에서 평균 통과율이 높고 0.8 이상이다(실행 3개 eval 이상, 두 구성 모두 측정)
  CHECK: python tools/check_benchmark.py .workspace/doc-automation-workspace/iteration-1/benchmark.json --min-evals 3 --min-pass 0.8
  EXPECT: BENCHMARK OK
  DEPS: tools/check_benchmark.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:10:39.652Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=5c7fb4fe1f1958f1b995eb51025338496c73055580875f376ab4b0c84bd69f0f; output-bytes=259

- [x] P9: 사람 검토용 정적 eval 뷰어 HTML이 생성되었고 모든 eval 실행을 포함한다
  CHECK: python tools/check_review_html.py .workspace/doc-automation-workspace/iteration-1/review.html .workspace/doc-automation-workspace/iteration-1
  EXPECT: REVIEW HTML OK
  DEPS: tools/check_review_html.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T07:10:40.106Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=ff716bb67e6a4a497dc50fb7b74ca8d70da7e1b78f9c1a782b1f5c66ef4cb645; output-bytes=46

- [ ] P10: doc-automation description의 트리거 평가에서 should-trigger 적중률 0.8 이상, near-miss 오발동률 0.2 이하
  CHECK: python tools/check_trigger_results.py .workspace/doc-automation-workspace/trigger/results.json --min-recall 0.8 --max-fpr 0.2
  EXPECT: TRIGGER OK
  DEPS: tools/check_trigger_results.py
  EVIDENCE: pending

- [x] P11: 계획서 진행 현황·CHANGELOG·README가 Phase 1 doc-automation 결과(측정값 포함)로 갱신되었다
  EVIDENCE: manual 2026-10-01 계획서 '진행 현황 > Phase 1' 표(통과율 0.79→1.00, 시간 340→281초, 발견·수정 11건), CHANGELOG 2.0.0-alpha.1 항목, README 스킬 표에 hwpx-editor 추가, docs/03-analysis/doc-automation-phase1.analysis.md 신설, handoff H10 추가 — 파일 직접 확인

ABANDON: P10 이 PC의 Claude CLI(npm 2.1.250, 데스크톱 2.1.281 모두) 헤드리스 실행이 'OAuth session expired'로 인증 실패해 claude -p 기반 실측 불가. Windows 호환 러너(tools/run_trigger_eval.py)와 판정기(tools/check_trigger_results.py), 질의 20개는 준비 완료. 대리 라우팅 지표 10/10·오발동 0은 참고용. 사용자 `claude login` 후 실행하도록 docs/gate0-handoff.md H10으로 이관.
