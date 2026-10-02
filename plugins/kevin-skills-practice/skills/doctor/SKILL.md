---
name: doctor
description: claude-skills 플러그인(업무·크리에이터) 스킬을 쓰기 전에 이 PC의 준비 상태를 점검한다. Python 버전, 필수 패키지, ffmpeg·yt-dlp·uv·LibreOffice, 한글 폰트, 작업 폴더 쓰기 권한, 디스크, 선택적으로 네트워크를 확인하고 실패 항목마다 이 OS용 해결 명령을 알려 준다. "환경 점검해줘", "실습 준비됐는지 확인", "스킬이 안 돌아가", "설치 확인", "doctor", "강의 전 점검"처럼 설치·환경 문제를 묻는 요청에 사용한다.
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
---

# 사전 점검(doctor)

스킬이 실패하는 가장 흔한 원인은 스킬 자체가 아니라 환경이다. 패키지 누락, ffmpeg 미설치, 한글 폰트 부재가 대표적이다.
이 스킬은 실습·업무 전에 그 원인을 한 번에 찾아낸다.

## 절차

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 점검할 스킬을 정한다. 사용자가 말하지 않았으면 전체를 점검한다.
2. 실행한다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/doctor.py
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/doctor.py --skills doc-automation meeting-minutes
   ```

3. 네트워크 확인은 외부 접속이 생기므로 사용자가 원하거나 강의 전 점검일 때만 `--network`를 붙인다.
4. 결과를 요약한다.
   - 스킬별 준비 상태(OK·WARN·FAIL)를 먼저 말한다.
   - FAIL 항목은 출력된 해결 명령을 그대로 보여 준다.
   - WARN은 어떤 선택 기능이 영향을 받는지 한 줄로 설명한다.
5. 해결 명령은 사용자가 실행하도록 안내한다. 사용자가 명시적으로 부탁할 때만 대신 실행한다. 설치는 시스템을 바꾸기 때문이다.

## 판정 기준

| 판정 | 의미 |
|------|------|
| FAIL | 해당 스킬의 핵심 기능이 동작하지 않는다 |
| WARN | 일부 선택 기능만 영향을 받는다 |
| OK | 준비됨 |

## 참고

- 기계 판독 결과가 필요하면 `--json`, 실패 시 종료 코드 1이 필요하면 `--strict`.
- 실행 환경 판정 근거는 `scripts/_vendor/env.py`, 한글 폰트는 `scripts/_vendor/fonts.py`로 따로 볼 수 있다.
- 환경 규약 전체: `references/_shared/environment.md`
