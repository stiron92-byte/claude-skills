# 사용자 맞춤(오버라이드) 규약

스킬을 회사·팀·개인 업무에 맞추는 표준 방법이다. 플러그인 설치 폴더를 직접 고치지 않는다.
설치 폴더의 수정은 플러그인 업데이트 때 사라지기 때문이다.

## 1. 맞춤 수준

가장 낮은 수준부터 시도한다. 낮을수록 쉽고 업데이트에 안전하다.

| 수준 | 바꾸는 것 | 방법 |
|:---:|-----------|------|
| L0 설정 | 기본값(출력 형식, 회사명, 보고 대상, 언어) | `settings.yaml` |
| L1 자산 | 회사 템플릿, 양식, 브랜드 보이스, 용어집 | 같은 상대 경로에 파일 배치 |
| L2 지식 | 도메인 프로필, 플랫폼 스펙, 분석 관점 | references 파일 추가 |
| L3 복제 | 워크플로 자체 | 스킬을 새 이름으로 복제(이 규약 밖) |
| L4 신규 | 다른 목적의 업무 | skill-creator로 새 스킬 작성(이 규약 밖) |

## 2. 오버라이드 폴더와 탐색 순서

| 순서 | 위치 | 용도 |
|:---:|------|------|
| 1 | `<작업 폴더>/.claude/claude-skills/<스킬명>/` | 팀 공용(Git으로 공유) |
| 2 | `~/.claude/claude-skills/<스킬명>/` | 개인 기본값 |
| 3 | 스킬 폴더 | 기본값 |

먼저 발견된 파일을 쓴다. 상대 경로는 스킬 폴더 기준과 같다.
예: 기본 `templates/email/team.md`를 바꾸려면 `<작업 폴더>/.claude/claude-skills/doc-automation/templates/email/team.md`를 만든다.

## 3. 스킬이 해야 할 일

스킬은 작업을 시작할 때 적용된 오버라이드를 확인하고 사용자에게 한 줄로 알린다.

```bash
python scripts/_vendor/overrides.py --skill <스킬명> --skill-dir <이 스킬 폴더> --list
python scripts/_vendor/overrides.py --skill <스킬명> --skill-dir <이 스킬 폴더> --settings
```

- 템플릿·양식·참조 파일을 읽을 때는 `--resolve <상대경로>`로 실제 경로를 얻어 그 파일을 읽는다.
- 적용된 오버라이드가 있으면 "적용된 맞춤: 프로젝트 2개(templates/…, settings.yaml)"처럼 알린다. 사용자가 맞춤이 반영됐는지 확인할 수 있어야 한다.
- 오버라이드가 없으면 알리지 않는다.

## 4. settings 파일

`settings.yaml`은 한 줄에 `key: value` 하나만 쓴다. 중첩이 필요하면 `settings.json`을 쓴다.
병합 순서는 기본값 → 사용자 → 프로젝트이며 나중 값이 이긴다.

```yaml
# .claude/claude-skills/meeting-minutes/settings.yaml
default_role: PM
default_purpose: 팀 공유용
default_format: docx
```

각 스킬이 받는 키는 그 스킬 README의 "커스터마이즈 포인트" 표에 있다. 표에 없는 키는 무시된다.

## 5. 보호 규칙 — 오버라이드로 바뀌지 않는다

| id | 규칙 |
|----|------|
| no-overwrite-original | 원본 파일을 덮어쓰지 않는다. 결과는 항상 새 파일로 저장한다 |
| no-secrets-in-files | API 키·토큰·Webhook URL을 설정 파일이나 결과물에 기록하지 않는다 |
| no-investment-advice | 특정 자산의 매수·매도를 권유하지 않는다 |
| confirm-before-external-send | 개인정보·내부 문서를 외부 서비스로 보내기 전에 사용자에게 확인한다 |
| no-silent-data-fix | 이상값·오타 후보를 사람 확인 없이 자동 수정하지 않는다 |

오버라이드 내용이 이 규칙과 충돌하면 스킬은 보호 규칙을 따르고, 그 사실을 사용자에게 알린다.

## 6. 공유 전 검사

```bash
python scripts/_vendor/validate_overrides.py <작업 폴더>/.claude/claude-skills/<스킬명>
```

- 실행 코드(.py, .sh 등)는 오버라이드로 넣을 수 없다. 코드를 바꿔야 하면 L3(복제)로 간다.
- 비밀 정보로 보이는 값이 있으면 오류다. 환경 변수나 플러그인 설정으로 옮긴다.
- 보호 규칙을 무력화하는 듯한 문장은 경고로 알린다.
