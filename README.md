# Claude Skills Book

책 『압도적 스킬로 바로 쓰는 클로드 코워크×AI 자동화』에서 다루는 **업무 자동화 스킬 모음**입니다.
v2부터 용도에 따라 **플러그인 3개**로 나누어 배포합니다.

> **v2 개발 중(2.0.0-alpha.1)**: 이 브랜치는 고도화 작업 중입니다. 책과 같은 구성이 필요하면 `v1.6.1` 태그를 쓰세요.
> 계획과 진행 상황은 [docs/01-plan/skills-upgrade.plan.md](docs/01-plan/skills-upgrade.plan.md)에 있습니다.

## 빠른 시작

**Claude Code**에서 실행하세요.

```
/plugin marketplace add humanist96/claude-skills
/plugin install kevin-skills-book@kevin-claude-skills
```

필요에 따라 추가로 설치합니다.

```
/plugin install kevin-skills-creator@kevin-claude-skills     # 콘텐츠·영상(선택)
/plugin install kevin-skills-practice@kevin-claude-skills    # 책·강의 실습 샘플과 환경 점검
```

**클로드 코워크(Cowork)**에서는 설정 → 플러그인 → 마켓플레이스 추가에 `humanist96/claude-skills`를 입력하고 필요한 플러그인을 설치하세요.

설치하면 별도 명령어 없이 **자연어로 자동 트리거**됩니다.

```
이 PDF로 과장님 보고용 PPT 만들어줘     → doc-automation
이 결재문서 양식에서 담당자만 바꿔줘     → hwpx-editor
이 엑셀 정리하고 분석해줘               → excel-automation
회의록 정리해줘                         → meeting-minutes
반도체 트렌드 리서치해줘                → data-collector
2장 실습 파일 작업 폴더로 복사해줘       → practice-samples
실습 전에 내 PC 환경 점검해줘            → doctor
```

처음 설치했거나 스킬이 동작하지 않으면 실습 플러그인의 `doctor`로 환경을 먼저 점검하세요. 부족한 패키지·도구와 이 OS용 설치 명령을 알려 줍니다.

## 플러그인과 스킬

| 플러그인 | 대상 | 스킬 | 하는 일 |
|----------|------|------|---------|
| `kevin-skills-book` (업무) | 전 직원 | `doc-automation` | 자료(PDF·Word·PPT·HWPX·엑셀·웹)를 읽고 보고 대상에 맞춘 PPT·보고 메일 생성. 모든 숫자를 출처와 대조 |
| | | `hwpx-editor` | 한글(HWPX) 양식은 그대로 두고 글자만 교체·`{{변수}}` 채우기(양식 보존 검증) |
| | | `excel-automation` | 엑셀 데이터 정리·분석·시각화·멀티탭 취합 |
| | | `meeting-minutes` | 회의 녹음(로컬 STT)·텍스트를 역할·용도별 회의록으로 정리 |
| | | `data-collector` | 관심 분야 데이터 수집 → 과거·현재·전망 트렌드 보고서 (+ 자동화 코드 생성) |
| `kevin-skills-creator` (콘텐츠·영상) | 마케팅·홍보 | `content-research` | 트렌드·뉴스 기반 콘텐츠 주제와 캘린더 |
| | | `content-repurpose` | 원본 콘텐츠를 플랫폼별 게시물로 변환, 콘텐츠 감사·갭 분석 |
| | | `generate-shorts` | 롱폼 영상 → 세로 쇼츠·카드뉴스 |
| | | `narration-video` | 텍스트 → AI 이미지·TTS·자막·BGM 나레이션 영상 (Gemini API·MCP 서버 필요) |
| `kevin-skills-practice` (실습) | 수강생 | `practice-samples` | 책·강의 실습 샘플을 작업 폴더로 복사 |
| | | `doctor` | 스킬 사용 전 PC 준비 상태 점검 |

v1.6.1에서 업그레이드하는 경우: 플러그인 이름이 바뀌었습니다(`claude-skills-book@claude-skills` → `kevin-skills-book@kevin-claude-skills`). 최신 Claude Code가 `claude-`로 시작하거나 공식 플러그인처럼 읽히는 이름을 받지 않기 때문입니다. 기존 플러그인을 제거하고 위 명령으로 다시 설치하세요. 콘텐츠·영상 스킬 4개는 `kevin-skills-creator`로, 실습 샘플은 `kevin-skills-practice`로 옮겨졌습니다. 해당 플러그인을 추가로 설치하세요.

## 내 업무에 맞게 바꾸기

플러그인 설치 폴더를 직접 고치지 마세요. 업데이트 때 사라집니다.
대신 작업 폴더의 `.claude/claude-skills/<스킬명>/`(팀 공유) 또는 `~/.claude/claude-skills/<스킬명>/`(개인)에
회사 템플릿·양식·설정 파일을 두면 스킬이 그것을 먼저 씁니다.
규약은 각 스킬의 `references/_shared/overrides.md`에 있고, 사용자 가이드는 Phase 3에서 제공합니다.

## 요구사항

- [Claude Code](https://code.claude.com/docs) 또는 Claude 데스크톱 앱(Cowork)
- Python 3.10+ (스크립트가 있는 스킬)
- 스킬별 의존성은 각 스킬의 `scripts/requirements.txt`에 고정 버전으로 있습니다. 전이 의존성까지 맞추려면 저장소 루트의 `constraints.txt`를 함께 씁니다.

  ```bash
  python -m pip install -r <스킬 폴더>/scripts/requirements.txt -c constraints.txt
  ```

## 저장소 구조

| 경로 | 용도 |
|------|------|
| `plugins/<플러그인>/skills/<스킬>/` | **배포용** 스킬 본체. 수정은 여기서 한다 |
| `plugins/<플러그인>/evals/` | `claude plugin eval` 평가 케이스 |
| `shared/` | 공통 모듈 원본(환경 감지·한글 폰트·출력 경로·오버라이드·doctor). `tools/build.py`가 각 스킬의 `_vendor/`·`_shared/`로 복사한다 |
| `tools/` | 빌드·검증 도구. CI가 같은 명령을 실행한다 |
| `tests/` | 단위 테스트와 검증기 대조 테스트 |
| `docs/` | 계획서, 스킬·README 템플릿 |
| `chapter02-*/ ~ chapter12_*/` | **학습용** 책 챕터 스냅샷(원고·예제·실행 결과) |
| `.claude-plugin/marketplace.json` | 마켓플레이스 매니페스트 |

## 개발자용 검증 명령

```bash
python tools/build.py                       # shared/ → 각 스킬로 복사
python tools/validate_skills.py --baseline tools/validate-baseline.json
python -m unittest discover -s tests -p "test_*.py"
python tools/run_plugin_validate.py         # claude plugin validate --strict
```

전체 목록은 `.github/workflows/ci.yml`에 있습니다.
