# <스킬명>

> <한 줄 소개>
> 플러그인: `<kevin-skills-book | kevin-skills-creator | kevin-skills-practice>` · 책 <N>장

## 하는 일

<2~3문장. 입력 → 출력>

## 데모

| 이렇게 요청하면 | 이런 결과가 나온다 |
|-----------------|--------------------|
| "<실제 요청 예>" | <결과 파일·형식 요약> |

실습 샘플: `practice-samples` 스킬로 `<세트 id>` 세트를 복사해서 시험한다.

## 요구사항

| 항목 | 필수 | 설치 |
|------|:---:|------|
| Python 3.10+ | ✅ | |
| <패키지·도구> | | `python -m pip install -r scripts/requirements.txt -c <저장소>/constraints.txt` |

설치 확인: `doctor` 스킬 또는 `python scripts/_vendor/doctor.py --skills <스킬명>`

## 지원 환경

| Claude Code Win | Claude Code Mac | Cowork | claude.ai |
|:-:|:-:|:-:|:-:|
| <지원/확인 필요/미지원> | | | |

## 커스터마이즈 포인트

플러그인 설치 폴더를 고치지 말고 오버라이드 폴더에 파일을 둔다(`references/_shared/overrides.md`).
`<작업 폴더>/.claude/claude-skills/<스킬명>/` 또는 `~/.claude/claude-skills/<스킬명>/`

| 수준 | 대상 | 파일(스킬 폴더 기준 상대 경로) | 형식 | 예시 |
|:---:|------|-------------------------------|------|------|
| L0 | <설정 키> | `settings.yaml` → `<key>` | <값 형식> | `<key>: <값>` |
| L1 | <교체 가능한 자산> | `<templates/...>` | <형식> | |
| L2 | <추가 가능한 지식> | `<references/...>` | <형식> | |

보호 규칙(오버라이드로 바뀌지 않음): 원본 덮어쓰기 금지, 비밀 정보 파일 기록 금지, 투자 권유 금지, 외부 전송 전 확인, 이상값 자동 수정 금지.

## 데이터 흐름

| 데이터 | 외부 전송 경로 |
|--------|----------------|
| <입력 데이터> | <Claude / 외부 API / 없음> |

## 변경 이력

| 버전 | 변경 |
|------|------|
| <x.y.z> | <요약> |
