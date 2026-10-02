# Gates: Phase 1 — meeting-minutes 고도화 (계획서 §1.2(3), §4 Phase 1)

OWNS: plugins/kevin-skills-book/skills/meeting-minutes/**, plugins/kevin-skills-practice/skills/practice-samples/samples/meeting-minutes/**, plugins/kevin-skills-practice/skills/practice-samples/samples/catalog.json, shared/scripts/doctor.py, tools/**, tests/**, .github/workflows/ci.yml, docs/**, CHANGELOG.md, README.md, constraints.txt, GATES.p1-meeting-minutes.md, .workspace/**

Scope: meeting-minutes를 "입력 정규화(음성 STT 또는 텍스트) → 번호 붙은 발언 → 근거가 붙은 구조화 회의록(minutes.json) → 형식별 렌더링 → 검증 게이트"로 고도화한다. 실행 환경 가정을 없애고, 질문을 기본값 1회 확인으로 줄이며, 실습 정답표를 갖추고, v1.6.1 대비 평가에서 더 나은 결과를 증거로 남긴다.

- [x] M0: this ledger states outcomes that can fail
  CHECK: node C:/Users/Admin/.claude/skills/unlazy/scripts/gate-lint.mjs GATES.p1-meeting-minutes.md
  EXPECT: LINT OK
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:12:54.669Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=d392dd91cc35b23c247223a159fc3cac733ba70cacaff977aaaca95114bdb08b; output-bytes=170

- [x] M1: 실습 입력(녹음 3개 + 텍스트 녹취록 1개)의 정답표가 있고, 텍스트 녹취록은 재현 가능하게 생성되며 정답표와 일치한다
  CHECK: python tests/check_meeting_practice.py
  EXPECT: MEETING PRACTICE OK
  DEPS: tests/check_meeting_practice.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:12:55.354Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=94f1887aa47153f3937238e6c4189fdab205890808d5043023a0e7dd4fde0983; output-bytes=162

- [x] M2: transcribe.py가 고정 환경(PyAV 19)에서 mp3를 변환하고, 번호 붙은 발언·신뢰도 표시·이어하기를 지원하며, 한국어 녹음에서 정답표 핵심어를 일정 비율 이상 담는다
  CHECK: python tests/check_transcribe.py
  EXPECT: TRANSCRIBE OK
  DEPS: tests/check_transcribe.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:14:07.381Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=b9b3e47115a3a99d2adc9e29c43acf2b968b4d8030b7756ead12413cab2186ae; output-bytes=304

- [x] M3: prepare_transcript.py가 일반 텍스트·화자 표기·클로바노트·SRT·VTT를 같은 번호 붙은 발언 형식으로 바꾼다
  CHECK: python tests/check_prepare_transcript.py
  EXPECT: PREPARE TRANSCRIPT OK
  DEPS: tests/check_prepare_transcript.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:14:11.117Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=5a783a45d31d4a3acfecc17cafa1e736b53519cc3174e3862a5547402e5bd69d; output-bytes=122

- [x] M4: build_minutes.py가 minutes.json을 용도별(팀 공유·상위 보고·개인 기록·이메일) 마크다운·워드·노션·텍스트로 렌더링하고 결정·액션이 하나도 빠지지 않는다
  CHECK: python tests/check_build_minutes.py
  EXPECT: BUILD MINUTES OK
  DEPS: tests/check_build_minutes.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:14:18.910Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=b98a4fd234a1086657d159b6ac3d9ffadf1e92572312881b5c31c2cde0be7658; output-bytes=151

- [x] M5: verify_minutes가 근거 없는 결정·없는 발언 번호·지어낸 숫자·녹취에 없는 담당자·근거 없는 기한·누락된 항목·홍보 문구를 각각 잡아낸다(양성 대조)
  CHECK: python tests/check_verify_minutes.py
  EXPECT: VERIFY MINUTES CONTROL OK
  DEPS: tests/check_verify_minutes.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:14:24.916Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=fc51285fa53afb61fbde2ee3c6cdd186a0350920ca464ab32b12bed4e709459c; output-bytes=827

- [x] M6: meeting-minutes SKILL.md·README가 품질 규약을 충족한다
  CHECK: python tools/check_skill_quality.py meeting-minutes
  EXPECT: SKILL QUALITY OK
  DEPS: tools/check_skill_quality.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:14:25.414Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=61bf5a6a4f8195dbe1e4a9d99e009f642d717435186077653ebc764daed40d90; output-bytes=44

- [x] M7: 회귀 없음 — Phase 0·doc-automation·excel-automation 검증 전체가 통과한다
  CHECK: python tools/run_regression.py
  EXPECT: REGRESSION OK
  DEPS: tools/run_regression.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:18:32.273Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=372a6f77503902ddf9194f07d50be533b049d4a887f58dd3b638e3ad61b37212; output-bytes=1266

- [x] M8: skill-creator 형식 evals.json이 음성 입력·텍스트 입력·영어 회의를 다루고 검증 가능한 expectations를 가진다
  CHECK: python tools/check_skillcreator_evals.py meeting-minutes
  EXPECT: SKILLCREATOR EVALS OK
  DEPS: tools/check_skillcreator_evals.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:18:32.735Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=15b032e9378b636e535a9902c1da3886a93f5d702926228d01363a41d1c04884; output-bytes=74

- [x] M9: 새 meeting-minutes가 v1.6.1 대비 benchmark에서 평균 통과율이 높고 0.8 이상이다(3개 eval 이상, 두 구성 모두 측정, 최종 반복 기준 — iteration-1은 0.952 < 0.975로 실패해 결함을 고친 뒤 iteration-2에서 두 구성을 모두 다시 측정)
  CHECK: python tools/check_benchmark.py .workspace/meeting-minutes-workspace/iteration-2/benchmark.json --min-evals 3 --min-pass 0.8
  EXPECT: BENCHMARK OK
  DEPS: tools/check_benchmark.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:18:33.144Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=cc44dae1f6ad82e895a386df9ba199f5c7088622ee9459771bc8c7331e20dedd; output-bytes=259

- [x] M10: 사람 검토용 정적 eval 뷰어 HTML이 모든 실행을 포함한다
  CHECK: python tools/check_review_html.py .workspace/meeting-minutes-workspace/iteration-2/review.html .workspace/meeting-minutes-workspace/iteration-2
  EXPECT: REVIEW HTML OK
  DEPS: tools/check_review_html.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-02T00:18:33.683Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=6b49b3708a04518611064330a8e3ea8d3054db39f8ebe68165965ed83f9ed64b; output-bytes=45

- [x] M11: 계획서 진행 현황·CHANGELOG·분석 문서·handoff가 meeting-minutes 결과(측정값 포함)로 갱신되었다
  EVIDENCE: manual 2026-10-02 계획서 '진행 현황 > Phase 1 — meeting-minutes' 표(iteration-1 0.952<0.975 실패 → iteration-2 0.977 대 0.975 사실상 동률, 시간 327초 대 270초, 점수 밖 차이 STT 우회 6/6·홍보 문구 8/8, 발견·수정 8건, 회귀 30개), CHANGELOG 2.0.0-alpha.1 meeting-minutes·수정·실습 샘플 항목, docs/03-analysis/meeting-minutes-phase1.analysis.md 신설(정답표 가격 수정과 편향 방지 처리 공개), handoff H10에 meeting-minutes 트리거 추가·H11 디스크/Word 프로세스 확인 신설 — 파일 직접 확인, tools/check_docs.py DOCS OK
