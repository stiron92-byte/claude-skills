# 실행 환경 규약

이 문서는 모든 스킬이 공통으로 따르는 환경 규약이다. 스킬 본문에 특정 환경의 경로를 하드코딩하지 않기 위해 존재한다.
같은 스킬이 Claude Code(Windows·macOS), Cowork, claude.ai에서 모두 쓰인다.

## 1. 지금 어디서 실행 중인지 먼저 확인한다

```bash
python scripts/_vendor/env.py
```

결과의 `surface`가 판단 기준이다. 자동 판정이 불확실하면 `unknown`·`local`로 나온다. 그때는 아래 표의 "그 외" 열을 따른다.

| surface | 판정 근거 |
|---------|-----------|
| `claude-ai` | `/mnt/user-data` 폴더가 있음 |
| `claude-code` | 환경 변수 `CLAUDECODE=1` 또는 `CLAUDE_CODE_ENTRYPOINT` |
| `cowork` | 자동 판정하지 않음. `CLAUDE_SKILLS_SURFACE=cowork`로 지정 |
| `local` | 위 표식이 없음 |

## 2. 입력 파일

- 사용자가 첨부했거나 경로를 알려 준 파일을 입력으로 쓴다.
- claude.ai에서만 업로드 파일이 `/mnt/user-data/uploads/`에 있다. 다른 환경에서 이 경로를 찾지 않는다.
- 입력이 불분명하면 파일 경로를 사용자에게 묻는다.

## 3. 출력 위치

```bash
python scripts/_vendor/paths.py <스킬명> --create
```

| 우선순위 | 위치 |
|---------|------|
| 1 | 환경 변수 `CLAUDE_SKILLS_OUTPUT_DIR` 아래 `<스킬명>/` |
| 2 | claude.ai: `/mnt/user-data/outputs/<스킬명>/` |
| 3 | 그 외: `<작업 폴더>/output/<스킬명>/` |

원본 파일과 같은 경로에 결과를 쓰지 않는다. 원본 손상은 되돌릴 수 없기 때문이다.

## 4. 결과 전달

- `present_files` 도구가 있으면(claude.ai) 그것으로 파일을 보여 준다.
- 없으면 결과 파일 경로를 마크다운 링크로 알려 준다.
- `computer://` 같은 특정 환경 전용 링크를 쓰지 않는다.

## 5. 다른 스킬 참조

- 공식 문서 스킬(docx, pptx, xlsx, pdf)은 **이름으로** 참조한다. 예: "docx 스킬이 있으면 그 지침을 먼저 읽는다."
- `/mnt/skills/public/...` 같은 설치 경로를 적지 않는다. 환경마다 다르다.
- 해당 스킬이 없으면 이 스킬의 references에 있는 최소 절차를 따른다.

## 6. 명령 시간 제한

- `env.py` 결과의 `command_time_limit_sec`가 숫자이면 명령 하나가 그 시간 안에 끝나야 한다(Cowork 약 45초).
- 이때는 긴 작업을 단계로 나누고, 중간 결과를 캐시하고, 같은 명령을 다시 실행하면 이어서 진행되게 한다.
- 백그라운드 실행은 명령이 끝나면 정리될 수 있으므로 해결책이 아니다.

## 7. 운영체제 차이

| 항목 | 규칙 |
|------|------|
| 한글 폰트 | `python scripts/_vendor/fonts.py`로 찾는다. 경로를 하드코딩하지 않는다 |
| 경로 구분자 | 스킬 문서와 명령 예시는 `/`를 쓴다. Python은 `pathlib`을 쓴다 |
| 셸 | 명령 예시는 bash와 PowerShell에서 모두 동작하는 형태로 쓴다. 파이프·리다이렉션이 필요하면 Python 스크립트로 옮긴다 |
| 패키지 설치 | `python -m pip install ...`. `--break-system-packages`는 claude.ai 컨테이너에서만 필요할 때 쓴다 |
| ffmpeg 필터 경로 | Windows 경로는 `fonts.ffmpeg_fontfile()`로 이스케이프한다 |

## 8. 준비 상태 점검

설치 직후나 오류가 나면 사전 점검을 실행한다.

```bash
python scripts/_vendor/doctor.py --skills <스킬명>
```
