# Gates: Phase 1 — content-repurpose 고도화 (계획서 §1.2(6), §4 Phase 1)

OWNS: plugins/kevin-skills-creator/skills/content-repurpose/**, plugins/kevin-skills-practice/skills/practice-samples/samples/content-repurpose/**, plugins/kevin-skills-practice/skills/practice-samples/samples/catalog.json, tools/**, tests/**, .github/workflows/ci.yml, docs/**, CHANGELOG.md, README.md, GATES.p1-content-repurpose.md, .workspace/**

Scope: content-repurpose를 "원본 정리(핵심 메시지·숫자) → 플랫폼별 생성(선택한 플랫폼 스펙만 읽음) → 글자 수·형식·원본 충실도 자동 검사"와 "목록 집계 스크립트 기반 감사·갭 분석"으로 고도화한다. 환경 종속 지시와 불필요한 금지 지시를 없애고, 원본 실습 자료와 정답표를 갖추며, v1.6.1 대비 평가에서 결과를 증거로 남긴다.

- [x] R0: this ledger states outcomes that can fail
  CHECK: node C:/Users/Admin/.claude/skills/unlazy/scripts/gate-lint.mjs GATES.p1-content-repurpose.md
  EXPECT: LINT OK
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:12:36.086Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=fb1455885e26bde8c1d20e469de035205e5bcbf23d73bc6d8ca3177950a01bfb; output-bytes=172

- [x] R1: 실습 원본(자체 작성 대본)과 정답표가 재현 가능하게 생성되고, 정답표의 핵심 메시지·숫자가 원본에서 확인되며, 제3자 녹취는 실습 입력에 쓰지 않는다
  CHECK: python tests/check_repurpose_practice.py
  EXPECT: REPURPOSE PRACTICE OK
  DEPS: tests/check_repurpose_practice.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:12:36.703Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=153f959ea501584417c66f3c24be4dbdee64f8b4d41d5994658ddb362b4c9a00; output-bytes=136

- [x] R2: count_chars.py가 플랫폼별 글자 수(X 가중치 포함)·해시태그 수·스레드 길이를 정확히 세고 한도 초과를 잡는다
  CHECK: python tests/check_count_chars.py
  EXPECT: COUNT CHARS OK
  DEPS: tests/check_count_chars.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:12:37.101Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=65d8e92b784cd704a79233070c9d43f8ddd16dfcb6e6583d5e566af6f46f1871; output-bytes=132

- [x] R3: check_repurpose.py가 한도 초과·자리표시·메타 레이블·코드 블록·서두 안내 문구·원본에 없는 숫자·빠진 플랫폼·필수 요소 누락을 각각 잡아낸다(양성 대조)
  CHECK: python tests/check_repurpose_verify.py
  EXPECT: REPURPOSE VERIFY CONTROL OK
  DEPS: tests/check_repurpose_verify.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:12:42.180Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=7755b57b2a6d9e7717b4338e69a54903ba1974714196aa343641491e9fd8337b; output-bytes=768

- [x] R4: content_inventory.py가 콘텐츠 목록을 읽어 카테고리 분포·경과 기간·중복 후보를 정확히 집계한다(책 실습 8-1 목록 기준)
  CHECK: python tests/check_content_inventory.py
  EXPECT: CONTENT INVENTORY OK
  DEPS: tests/check_content_inventory.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:12:44.081Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=996df9b42604b63a198985515e7f33514f4833eb8cad4b193505ac3550c6d1bf; output-bytes=177

- [x] R5: content-repurpose SKILL.md·README가 품질 규약을 충족한다
  CHECK: python tools/check_skill_quality.py content-repurpose
  EXPECT: SKILL QUALITY OK
  DEPS: tools/check_skill_quality.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:12:44.511Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=3ca2c02dc472d70494bd70bf987aeb6f59fb969c353b7373f81b8dc8eab315b5; output-bytes=46

- [x] R6: 회귀 없음 — Phase 0·앞선 Phase 1 스킬 검증 전체가 통과한다
  CHECK: python tools/run_regression.py
  EXPECT: REGRESSION OK
  DEPS: tools/run_regression.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:17:08.146Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=aa29b98051aab3c2359d0465b220087b7d50bd0ae45894214f5ba61801c796b3; output-bytes=1456

- [x] R7: skill-creator 형식 evals.json이 변환·감사·갭 분석을 다루고 책 실습 8-1·8-2 프롬프트를 원문 그대로 포함한다
  CHECK: python tools/check_skillcreator_evals.py content-repurpose
  EXPECT: SKILLCREATOR EVALS OK
  DEPS: tools/check_skillcreator_evals.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:17:08.602Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=333062dba5f805a1f294ec6f181bb64cf77a47d79a305359e12f8d6028c797b5; output-bytes=76

- [ ] R8: 새 content-repurpose가 v1.6.1 대비 benchmark에서 평균 통과율이 높고 0.8 이상이다(3개 eval 이상, 두 구성 모두 측정, 최종 반복 기준 — iteration-1은 두 구성 모두 1.00으로 판별 불가(천장 효과), 계획서의 사전 위험에 근거한 eval 2개를 실행 전에 추가해 iteration-2에서 6개 eval을 두 구성 모두 다시 측정)
  CHECK: python tools/check_benchmark.py .workspace/content-repurpose-workspace/iteration-2/benchmark.json --min-evals 3 --min-pass 0.8
  EXPECT: BENCHMARK OK
  DEPS: tools/check_benchmark.py
  EVIDENCE: pending

ABANDON: R8 iteration-1(4개 eval)과 iteration-2(사전 위험 근거로 실행 전에 추가한 2개 포함 6개 eval) 모두 with_skill 1.000 vs old_skill 1.000 동률로 측정되어(check_benchmark FAIL, 천장 효과) 새 스킬이 더 높다는 결과가 나오지 않았다. 강한 모델(Opus 5.5)은 v1.6.1 지시만으로도 한도·숫자·형식을 지켰다. 결과를 본 뒤 v1.6.1이 실패할 eval을 골라 추가하는 것은 공정하지 않으므로 여기서 멈추고, 약한 모델이나 실제 사용자 세션 측정으로 넘긴다(docs/gate0-handoff.md H12).

- [x] R9: 사람 검토용 정적 eval 뷰어 HTML이 모든 실행을 포함한다
  CHECK: python tools/check_review_html.py .workspace/content-repurpose-workspace/iteration-2/review.html .workspace/content-repurpose-workspace/iteration-2
  EXPECT: REVIEW HTML OK
  DEPS: tools/check_review_html.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T01:17:09.071Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=20de43b1a14546e7934fb652271ba7028f0325b475d2348f65fa69dac3f8d069; output-bytes=46

- [x] R10: 계획서 진행 현황·CHANGELOG·분석 문서·handoff가 content-repurpose 결과(측정값 포함)로 갱신되었다
  EVIDENCE: manual 2026-10-02 — docs/01-plan/skills-upgrade.plan.md 'Phase 1 — content-repurpose' 표(1.00 대 1.00 동률·R8 포기·회귀 34개, 다음 data-collector), CHANGELOG.md content-repurpose 섹션·8장 실습 샘플 줄, docs/03-analysis/content-repurpose-phase1.analysis.md(§2 두 반복 측정값, §3 채점기 수정 6건, §4 결함 9건), docs/gate0-handoff.md H12 추가·H10에 content-repurpose 포함. 각 문서를 열어 측정값이 benchmark.json(iteration-1·2)과 일치함을 확인
