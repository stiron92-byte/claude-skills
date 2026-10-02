# Gates: Phase 1 — excel-automation 고도화 (계획서 §1.2(2), §4 Phase 1)

OWNS: plugins/kevin-skills-book/skills/excel-automation/**, plugins/kevin-skills-book/evals/**, plugins/kevin-skills-practice/skills/practice-samples/samples/excel-automation/**, plugins/kevin-skills-practice/skills/practice-samples/samples/catalog.json, shared/scripts/doctor.py, tools/**, tests/**, .github/workflows/ci.yml, docs/**, CHANGELOG.md, README.md, GATES.p1-excel-automation.md, .workspace/**

Scope: excel-automation을 "프로파일 → 기능 판단 → 결정적 엔진(정리·취합) + 분석 도구 → 재계산 → 검증 게이트"로 고도화하고, 결과물이 아니라 진짜 원본인 실습 입력(정답표 포함)을 갖추며, v1.6.1 대비 평가에서 더 나은 결과를 증거로 남긴다.

- [x] E0: this ledger states outcomes that can fail
  CHECK: node C:/Users/Admin/.claude/skills/unlazy/scripts/gate-lint.mjs GATES.p1-excel-automation.md
  EXPECT: LINT OK
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:17:33.279Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=85bc8af645b301fef7b2e93e7748ca377e30d33a031931195ff9c66a7c3d3028; output-bytes=171

- [x] E1: 실습 원본 3종이 재현 가능하게 생성되고 정답표와 일치하며, 기존 결과물은 완성 예시로 재분류되었다
  CHECK: python tests/check_excel_practice_inputs.py
  EXPECT: PRACTICE INPUTS OK
  DEPS: tests/check_excel_practice_inputs.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:17:41.077Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=4f2837216ac13367c7d338a05ce4e4730eefbe7a295262a1b19c398d260e8888; output-bytes=124

- [x] E2: 정리 엔진이 실습1 원본에서 정답표와 같은 결과(중복 제거, 전화·날짜 정규화, 이상값 비수정 보고, 이메일 오타 후보)를 내고 원본을 바꾸지 않는다
  CHECK: python tests/check_excel_clean.py
  EXPECT: EXCEL CLEAN OK
  DEPS: tests/check_excel_clean.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:17:45.582Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=eff6899b027295e675017689beea160022281eb75ae52548ea2a6c38c8fe663d; output-bytes=131

- [x] E3: 취합 엔진이 실습3 원본을 원본 시트 보존 + 수식 기반 통합관리 시트로 만들고, 재계산 결과가 직접 계산값과 일치하며 수식 오류가 0이다
  CHECK: python tests/check_excel_consolidate.py
  EXPECT: EXCEL CONSOLIDATE OK
  DEPS: tests/check_excel_consolidate.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:18:08.219Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=9eef8ea6492a53face594bd26ffa6be6d7e9beb7c1eb105fd8f416a41c049e9d; output-bytes=157

- [x] E4: verify_excel이 원본 변경·행 수 불일치·수식 오류·출처 없는 인사이트 숫자·원본 시트 누락을 각각 잡아낸다(양성 대조)
  CHECK: python tests/check_verify_excel.py
  EXPECT: VERIFY EXCEL CONTROL OK
  DEPS: tests/check_verify_excel.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:19:18.284Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=d6d14a5a7d544b1addb9c740b533c5c25aaab3d6f945f98992fa4e0b1f7784ca; output-bytes=760

- [x] E5: excel-automation SKILL.md·README가 품질 규약을 충족한다
  CHECK: python tools/check_skill_quality.py excel-automation
  EXPECT: SKILL QUALITY OK
  DEPS: tools/check_skill_quality.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:19:18.750Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=169b8e1079f151a5ed4d2d16684f0be3e0ce4221fc7c81d1f20cfca05055a60b; output-bytes=45

- [x] E6: 회귀 없음 — Phase 0·doc-automation 검증 전체가 통과한다
  CHECK: python tools/run_regression.py
  EXPECT: REGRESSION OK
  DEPS: tools/run_regression.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:21:43.348Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=da5c60cd796869b77a26ddc445de7e47a29acb1f6c2dec2cac8668d1fac54500; output-bytes=1048

- [x] E7: skill-creator 형식 evals.json이 정리·분석·취합 세 기능을 각각 다루고 검증 가능한 expectations를 가진다
  CHECK: python tools/check_skillcreator_evals.py excel-automation
  EXPECT: SKILLCREATOR EVALS OK
  DEPS: tools/check_skillcreator_evals.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:21:43.808Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=4f9a5b57f6230e383348aa4a94c0583b50be49f37b3afda050f6c8ed341bf90a; output-bytes=75

- [x] E8: 새 excel-automation이 v1.6.1 대비 benchmark에서 평균 통과율이 높고 0.8 이상이다(3개 eval, 두 구성 모두 측정)
  CHECK: python tools/check_benchmark.py .workspace/excel-automation-workspace/iteration-1/benchmark.json --min-evals 3 --min-pass 0.8
  EXPECT: BENCHMARK OK
  DEPS: tools/check_benchmark.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:21:44.275Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=ec0a9c11b2d0afe4a181ed4c3f6f40dbc6636abca36f72e7c541973a84612ebf; output-bytes=218

- [x] E9: 사람 검토용 정적 eval 뷰어 HTML이 모든 실행을 포함한다
  CHECK: python tools/check_review_html.py .workspace/excel-automation-workspace/iteration-1/review.html .workspace/excel-automation-workspace/iteration-1
  EXPECT: REVIEW HTML OK
  DEPS: tools/check_review_html.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T08:21:44.658Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=e88f526c4a74ca483040595b87cb99a15b46c9e8fab69388d028e800f2c886d6; output-bytes=45

- [x] E10: 계획서 진행 현황·CHANGELOG·분석 문서·handoff가 excel-automation 결과(측정값 포함)로 갱신되었다
  EVIDENCE: manual 2026-10-01 계획서 '진행 현황 > Phase 1 — excel-automation' 표(통과율 0.93→1.00, 시간 245→148초, 발견·수정 6건, 회귀 25개), CHANGELOG 2.0.0-alpha.1 excel-automation·실습 샘플 항목, docs/03-analysis/excel-automation-phase1.analysis.md 신설, handoff H10에 excel 트리거 측정 추가 — 파일 직접 확인. tools/check_docs.py DOCS OK
