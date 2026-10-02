# Gate 0 — 사용자·조직 조치 항목 (handoff)

> 작성: 2026-10-01 · 근거: 계획서 §7.1~7.3, D6·D8·D9
> 이 항목들은 코드로 해결할 수 없고, 사내 배포나 외부 강의 공개 **전에** 담당자가 처리해야 한다.
> Phase 0 기술 작업은 진행됐지만, 아래가 끝나기 전에는 v2를 외부에 배포하지 않는다.

| # | 조치 | 담당(제안) | 근거 | 상태 |
|---|------|-----------|------|------|
| H1 | 원저작자에게 사내 배포·강의 사용·수정에 대한 **서면 허락** 요청. 허락 범위에 맞춰 LICENSE 또는 사내 전용 고지를 정한다. 허락을 못 받으면 클린룸 재작성으로 전환한다 | 플러그인 오너 | 저장소에 LICENSE 없음, GitHub 라이선스 미지정. 23/28 커밋이 원저작자 계정 | 미착수 |
| H2 | 플러그인 매니페스트 `license` 필드 결정 | 플러그인 오너 + 법무 | H1 결과에 따름. 현재 의도적으로 비워 둠 | H1 대기 |
| H3 | 실습 샘플 제3자 저작물 권리 확인: **환율 주간 리포트 PDF**(금융기관 리포트로 보임), 팁스 공고 hwpx(공공누리 유형 확인), 삼성전자 투자분석 pptx(투자 오인 문구 점검) | 강사 + 법무 | `samples/catalog.json`의 `rights` 메모. 권리 미확인 시 자체 제작 샘플로 교체 | 미착수 |
| H4 | 책 원고 성격 파일(`chapter*/book-chapter-*.md`, `chapter08*/7_*_rewrite*.md`, 부록 PDF)의 출판 계약상 권리 확인, 외부 배포본에서 제외 여부 결정 | 플러그인 오너 | 계획서 §7.1 | 미착수 |
| H5 | 정보보호팀 검토: 스킬별 데이터 흐름(계획서 §7.2 표), Gemini API 사용 승인 여부, YouTube 다운로드 범위 | 정보보호팀 | D8·D9. 결과에 따라 narration-video Full 모드·generate-shorts 기본 노출 결정 | 미착수 |
| H6 | AI 생성물 대외 게시 시 고지 의무(AI 기본법) 적용 여부 법무 검토 | 법무 | 계획서 §7.1 | 미착수 |
| H7 | GitHub fork 연결 정리(지원팀 분리 요청 또는 새 저장소 이전). 커밋 이력 재작성은 하지 않는다 | 플러그인 오너 | H1 이후에 진행 | H1 대기 |
| H8 | `claude plugin eval` 사용 권한 확보 후 smoke 케이스 실제 실행(GATES.md G9) | 플러그인 오너 | 현재 계정에서 early access | 대기 |
| H10 | Claude CLI 로그인(`claude login`) 후 doc-automation 트리거 실측: `python tools/run_trigger_eval.py --eval-set plugins/kevin-skills-book/skills/doc-automation/evals/trigger-eval.json --skill-path plugins/kevin-skills-book/skills/doc-automation --out .workspace/doc-automation-workspace/trigger` → `python tools/check_trigger_results.py .workspace/doc-automation-workspace/trigger/results.json` | 플러그인 오너 | GATES.p1 P10. 현재 CLI OAuth 만료로 헤드리스 실행 불가. excel-automation·meeting-minutes·content-repurpose도 같은 방식으로 트리거 세트(`evals/trigger-eval.json`)를 만든 뒤 측정한다 | 대기 |
| H11 | 이 PC의 C 드라이브 여유 공간 확보(작업 중 한때 0.3GB). 한국어 회의록 STT는 small 모델(465MB)이 기본이며, 공간이 없으면 정확도가 낮은 base로 대체된다. 평가 중 한 실행이 Word 자동화를 시도하다 거부되어 WINWORD.EXE가 남아 있을 수 있다(사용자 Word일 수도 있어 종료하지 않음) | 플러그인 오너 | meeting-minutes Phase 1 | 확인 필요 |
| H12 | content-repurpose 비교 평가 판별력 확보: 같은 6개 eval(`plugins/kevin-skills-creator/skills/content-repurpose/evals/evals.json`)을 약한 모델(Haiku·Sonnet)이나 실제 사용자 세션으로 v2·v1.6.1 각각 반복 실행해 차이를 측정한다. Opus 5.5 1회 실행에서는 두 반복 모두 1.00 대 1.00 동률이었다(GATES.p1-content-repurpose R8 ABANDON). 트리거 실측과 generate-shorts와의 경계 측정도 함께(H10의 CLI 로그인 필요) | 플러그인 오너 | content-repurpose Phase 1 | 대기 |
| H9 | 사내 배포 경로 결정: 사내 GitHub Enterprise 정본 + 강의용 태그 공개 미러, 관리형 설정으로 마켓플레이스 등록 | 플러그인 오너 + IT | D10 | 미착수 |

## 이 PC의 doctor 점검 결과 (참고)

Phase 0 검증 중 `doctor`가 이 PC에서 찾은 부족 항목이다. 강의 시연 PC라면 미리 설치한다.

| 항목 | 영향 스킬 | 해결 명령 |
|------|-----------|-----------|
| matplotlib 없음 | doc-automation(필수), excel-automation(선택) | `python -m pip install matplotlib` |
| ffmpeg 없음 | generate-shorts, narration-video(필수), meeting-minutes(선택) | `winget install Gyan.FFmpeg` |
| uv 없음 | narration-video | `winget install astral-sh.uv` |
| feedparser 없음 | content-research(선택) | `python -m pip install feedparser` |
