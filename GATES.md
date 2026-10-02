# Gates: Phase 0 — 공통 기반 (docs/01-plan/skills-upgrade.plan.md §4 Phase 0, D3·D7·D11 권장안)

OWNS: .claude-plugin/**, plugins/**, shared/**, tools/**, tests/**, .github/**, docs/templates/**, docs/gate0-handoff.md, docs/01-plan/skills-upgrade.plan.md, README.md, CHANGELOG.md, .gitignore, .gitattributes, constraints.txt, GATES.md, chapter02-doc-automation/example/example_3_comany-to-ppt/*.docx, chapter09-generate-shorts/scripts/setup.sh, chapter10-narration-video/scripts/setup.sh

Scope: 스킬 8개를 업무·크리에이터·실습 3개 플러그인으로 재구성하고, 공통 모듈 vendoring·정적 검증·CI·eval 골격·의존성 고정·사전 점검·오버라이드 규약·템플릿·baseline을 갖춘다. 스킬 본문 품질 개선(Phase 1)은 범위 밖이다.

- [x] G0: this ledger states outcomes that can fail
  CHECK: node C:/Users/Admin/.claude/skills/unlazy/scripts/gate-lint.mjs GATES.md
  EXPECT: LINT OK
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:42.452Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=a4bef8ef67f02352929083ac40732296f8c332046efd6df58701089cc26ecdc8; output-bytes=384

- [x] G1: 마켓플레이스와 3개 플러그인 manifest가 공식 검증기를 통과한다
  CHECK: python tools/run_plugin_validate.py
  EXPECT: PLUGIN VALIDATE OK
  DEPS: tools/run_plugin_validate.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:47.873Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=309adc0f5f2509ae3f2962151554edc3d87766e5d0bc9d2e9f128d28e3b87aef; output-bytes=298

- [x] G2: 기존 스킬 8개가 빠짐없이 지정 플러그인으로 이동했고 v1.6.1 대비 스킬 파일 내용 손실이 없다
  CHECK: python tools/check_migration.py
  EXPECT: MIGRATION OK
  DEPS: tools/check_migration.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:54.044Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=6a0f7ccfac2cfe221703e5ba1edddb5ac2d9ff9018d87df18044597176e85f4a; output-bytes=94

- [x] G3: shared 모듈이 모든 대상 스킬에 동일하게 vendoring되어 있다
  CHECK: python tools/build.py --check
  EXPECT: VENDOR IN SYNC
  DEPS: tools/build.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:54.476Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=7d3de283a88df6cf4bff94ad3c0cf52751f7289e5ea1583279a2018a0eff859c; output-bytes=51

- [x] G4: 정적 스킬 검증기가 현재 트리를 baseline 대비 신규 위반 0건으로 통과한다
  CHECK: python tools/validate_skills.py --baseline tools/validate-baseline.json
  EXPECT: VALIDATE OK
  DEPS: tools/validate_skills.py, tools/validate-baseline.json
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:55.059Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=3396738c5d1361760546bac8c3e799643604490592700abae084da344fd32c95; output-bytes=162

- [x] G5: 정적 검증기가 금지 경로를 새로 넣은 스킬을 실제로 잡아낸다 (양성 대조군)
  CHECK: python tests/control_validator_detects.py
  EXPECT: CONTROL DETECTED
  DEPS: tests/control_validator_detects.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:56.069Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=9842940110c7dc3eb5b4666d562f561ba029426deaaac63a4b6c9f5ed8a84664; output-bytes=128

- [x] G6: shared 스크립트(폰트·환경·경로·오버라이드·오버라이드 검증·doctor) 단위 테스트가 모두 통과한다
  CHECK: python -m unittest discover -s tests -p "test_*.py" -v
  EXPECT: /Ran [1-9][0-9]* tests?[\s\S]*\nOK/
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:58.606Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=01a2fa3a1bde643ae6f7fe4ae5cf62ebb9f5ac824ea59050e638d74e96342185; output-bytes=3653

- [x] G7: 모든 Python 스크립트가 바이트 컴파일된다
  CHECK: python tools/compile_all.py
  EXPECT: COMPILE OK
  DEPS: tools/compile_all.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:59.143Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=b5d10e0b1846c0bf2dd52c9159fc7e8a6491d07dda92392031f510fbaeafec1a; output-bytes=51

- [x] G8: eval 케이스 골격이 스킬 8개 + 실습 스킬 전부에 존재하고 문서화된 형식을 따른다
  CHECK: python tools/check_evals.py
  EXPECT: EVALS OK
  DEPS: tools/check_evals.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:25:59.463Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=fae66ca23ebbeaa913f7385c43b29b051c5ad87588a58161b911fc672a680fc5; output-bytes=43

- [ ] G9: eval 케이스가 실제 claude plugin eval 런타임에서 실행된다
  EVIDENCE: pending

- [x] G10: 의존성 파일이 모두 고정 버전(사유가 기록된 예외 제외)·ASCII이고, 깨끗한 가상환경에 함께 설치·import되며 결과가 constraints.txt와 일치한다
  CHECK: python tools/check_pins.py --install
  EXPECT: PINS OK
  DEPS: tools/check_pins.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:24:44.066Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=480676e5b51417c69ba3806d5c24decc003949419604c604d81c13448dd5ac61; output-bytes=102

- [x] G11: doctor가 이 PC에서 실행되어 항목별 판정과 해결 명령을 JSON으로 낸다
  CHECK: python tools/check_doctor.py
  EXPECT: DOCTOR OK
  DEPS: tools/check_doctor.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:00.820Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=38b22ae24eefd9ebb8c1fc0cc962bb162461a3b081b355615f791af6d12fef03; output-bytes=287

- [x] G12: 예제 docx에서 내장 폰트가 제거되었고 문서가 정상적으로 열리며 본문 텍스트가 보존되었다
  CHECK: python tools/check_docx_slim.py
  EXPECT: DOCX SLIM OK
  DEPS: tools/check_docx_slim.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:03.148Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=ff55c22bc1e54fca4779b0dd2f2c24be62b9214fa7ac5a05660792e93c57fc0e; output-bytes=31

- [x] G13: 업무 플러그인 크기가 1MB 이하이고 샘플 바이너리를 포함하지 않는다
  CHECK: python tools/check_sizes.py
  EXPECT: SIZES OK
  DEPS: tools/check_sizes.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:03.615Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=236c228abcc1ead84af66018f54dd8481312cab903f670db7884ebcc64e0bae5; output-bytes=191

- [x] G14: CI 워크플로가 유효한 YAML이고 로컬 검증 명령과 같은 단계를 포함한다
  CHECK: python tools/check_ci.py
  EXPECT: CI OK
  DEPS: tools/check_ci.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:04.054Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=556f1a697f012cc9220d6d97b8f7f843dc5aebe33e62b984d89f332503097587; output-bytes=81

- [x] G15: baseline(v1.6.1 태그) 스냅샷이 재현 가능하게 생성된다
  CHECK: python tools/make_baseline.py --verify
  EXPECT: BASELINE OK
  DEPS: tools/make_baseline.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:11.941Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=2e4f6c6bc28db6dc60b8203ad53a8749921c713f6f386d6dd6bb7c582d7dcc5b; output-bytes=71

- [x] G16: 오버라이드 규약·환경 규약·SKILL/README 템플릿 문서가 필수 섹션을 갖추고 있다
  CHECK: python tools/check_docs.py
  EXPECT: DOCS OK
  DEPS: tools/check_docs.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:12.412Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=95a41d33cc5bf4ac73d5cf2e5872d2aded3ac7e000dfe7fc1a10177919c1a3e4; output-bytes=40

- [x] G17: 원 저장소 소유자 흔적이 작업 트리에 없다 (양성 대조군 포함)
  CHECK: python tools/check_traces.py
  EXPECT: TRACES CLEAN
  DEPS: tools/check_traces.py
  EVIDENCE: exit=0; shell=C:\WINDOWS\system32\cmd.exe; verified-at=2026-10-01T06:26:13.212Z; cwd=C:\@Work\claude-cowork-plugin\claude-skills; path=00b5b12e4153/36 entries; EXPECT=matched; output-sha256=4147cf6b9592b353b4c2ab5dcfb52198fb66a91d085c562e41361b2b61476307; output-bytes=51

- [x] G18: Gate 0 사용자 조치 항목(원저작자 허락, 제3자 샘플 권리, 보안 검토)이 handoff 문서에 담당·근거와 함께 기록되었다
  EVIDENCE: manual 2026-10-01 docs/gate0-handoff.md 표 H1~H9 9행, 각 행에 담당·근거·상태 열 존재 확인(H1 원저작자 허락, H3 제3자 샘플, H5 보안 검토 포함)

ABANDON: G9 claude plugin eval이 이 계정에서 early access로 비활성(`claude plugin eval init --bare` 실행 시 'currently in early access' 출력). 케이스는 G8로 형식만 검증됨. 권한 확보 후 실행하도록 docs/gate0-handoff.md H8로 이관.
