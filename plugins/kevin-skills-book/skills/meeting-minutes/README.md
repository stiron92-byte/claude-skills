# meeting-minutes

> 회의 녹음이나 녹취 텍스트로 회의록을 만든다. 결정·할 일마다 근거 발언을 붙여 녹취와 대조한다.
> 플러그인: `kevin-skills-book` · 책 4장

## 하는 일

입력을 번호 붙은 발언(T0001…)으로 바꾼다.

- **음성:** `transcribe.py`가 로컬 faster-whisper로 변환한다. 음성은 외부로 보내지 않는다.
- **텍스트:** `prepare_transcript.py`가 클로바노트·노션·SRT·VTT·워드·화자 표기를 같은 형식으로 정리한다.

Claude가 녹취를 끝까지 읽고 `minutes.json`에 정리한다. 결정, 할 일(담당자·기한), 미결, 다음 회의, 확인 필요 항목이 들어가고, 항목마다 근거 발언 번호가 붙는다.
`verify_minutes.py`가 근거·담당자·기한·숫자·참석자를 녹취와 대조한다. 통과하면 `build_minutes.py`가 용도별(팀 공유·상위 보고·개인 기록·이메일)로 마크다운·워드·노션·텍스트 문서를 만든다.

## 데모

| 이렇게 요청하면 | 이런 결과가 나온다 |
|-----------------|--------------------|
| "test_sprint_meeting_ko.mp3 회의록 정리해서 팀 슬랙에 올릴 거야" | 팀 공유용 마크다운: 결정 2개, 할 일 5개(담당자·기한), 다음 회의, STT로 확정 못 한 시각은 '확인 필요' |
| "기획 회의 녹음으로 부장님 보고용 워드 만들어줘" | 결론 먼저 쓴 보고용 워드, 근거 발언 대조표 포함 |
| "이 클로바노트 녹취로 회의록, 할 일은 노션에 붙일 거야" | 노션용 마크다운(할 일 체크박스), 번복된 안은 결정에서 제외, 담당자 없는 일은 '미정' |
| "영어 회의 녹음 요약해서 메일로 보낼 수 있게" | 영어 머리말의 이메일 본문(제목 줄·인사·결정·할 일·맺음) |

실습 샘플은 `practice-samples` 스킬로 복사해서 쓴다.

| 세트 | 내용 |
|------|------|
| `meeting-recordings` | 녹음 3개(한국어 2, 영어 1) |
| `meeting-text` | 클로바노트 형식 녹취록 |
| `meeting-answer-key` | 강사용 정답표 |

## 요구사항

| 항목 | 필수 | 설치 |
|------|:---:|------|
| Python 3.10+ | ✅ | |
| python-docx | 워드 출력 시 | `python -m pip install -r scripts/requirements.txt -c <저장소>/constraints.txt` |
| faster-whisper(PyAV 포함) | 음성 입력 시 | 위 명령에 포함. ffmpeg 별도 설치는 필요 없다 |
| 디스크 | 음성 입력 시 | 모델 내려받기 base 145MB, small 465MB(한국어 기본) |

설치는 `doctor` 스킬이나 다음 명령으로 확인한다. 텍스트 입력만 쓰면 추가 설치가 필요 없다.

```bash
python scripts/_vendor/doctor.py --skills meeting-minutes
```

## 지원 환경

| Claude Code Win | Claude Code Mac | Cowork | claude.ai |
|:-:|:-:|:-:|:-:|
| 지원 | 지원 | 지원(긴 녹음은 실행 시간 제한에 주의, `--resume` 또는 텍스트 입력) | 텍스트 입력 지원. 음성은 컨테이너에 패키지·모델이 있어야 함 |

## 커스터마이즈 포인트

플러그인 설치 폴더를 고치지 말고 오버라이드 폴더에 파일을 둔다. 규약은 `references/_shared/overrides.md`에 있다.

- 팀 공용: `<작업 폴더>/.claude/claude-skills/meeting-minutes/`
- 개인 기본값: `~/.claude/claude-skills/meeting-minutes/`

| 수준 | 대상 | 파일(스킬 폴더 기준 상대 경로) | 형식 | 예시 |
|:---:|------|-------------------------------|------|------|
| L0 | 기본 역할 | `settings.yaml` → `default_role` | 문자열 | `default_role: PM` |
| L0 | 기본 용도 | `settings.yaml` → `default_purpose` | team·report·personal·email | `default_purpose: report` |
| L0 | 기본 형식 | `settings.yaml` → `default_format` | md·docx·notion·text | `default_format: docx` |
| L0 | STT 모델 | `settings.yaml` → `stt_model` | base·small·medium·large-v3-turbo | `stt_model: medium` |
| L1 | 참석자·용어 사전 | `references/glossary.md` | 마크다운 목록 | 팀원 이름, 제품명, 사내 약어 |
| L2 | 회의 유형별 구성 | `references/meeting-types.md` | 마크다운 | 주간회의는 KPI 표 필수, 고객 미팅은 고객 요청 섹션, 면접은 평가 항목 |

용어 사전은 기본적으로 회의록 단계의 오인식 교정 참고로 쓴다. `--hotwords`를 주면 음성 인식 힌트로도 쓰여, 샘플에서는 오인식하던 이름·용어 4개가 모두 바르게 나왔다. 다만 숫자가 많은 녹음에서는 오히려 금액을 잘못 들어 기본값으로 켜지 않았다(`references/stt.md`).

다음 보호 규칙은 오버라이드로 바뀌지 않는다.

- 원본 덮어쓰기 금지
- 비밀 정보 파일 기록 금지
- 외부 전송 전 확인(회의록 메일 발송 포함)
- 이상값 자동 수정 금지(STT 오인식 교정은 선언하고 근거를 단다)
- 투자 권유 금지

## 데이터 흐름

| 데이터 | 외부 전송 경로 |
|--------|----------------|
| 음성 | 없음. 로컬 faster-whisper로 변환한다(처음 한 번 모델 내려받기) |
| 녹취 텍스트 | Claude(회의록 정리). 번호 붙이기·검증·렌더링은 로컬 |

인사·영업 정보가 담긴 회의는 결과 파일 위치와 공유 범위를 사용자에게 확인한다.

## 변경 이력

| 버전 | 변경 |
|------|------|
| 2.0.0-alpha.1 | 근거 기반으로 재설계했다. 번호 붙은 녹취(transcribe·prepare_transcript), minutes.json, verify_minutes(근거·담당자·기한·숫자 대조), build_minutes(용도 4 × 형식 4)를 추가했다. 실행 환경 경로 가정과 '질문 3개 필수', 홍보 문구를 없앴다. STT 모델 자동 선택·용어 사전·이어하기를 추가하고, PyAV 15 이상에서 faster-whisper 디코딩이 실패하던 문제를 고쳤다. 텍스트 녹취 실습과 정답표를 추가했다 |
| 1.6.1 | 책 출간 시점(claude.ai 컨테이너 경로, 질문 3개 필수) |
