---
name: <스킬명 — 디렉터리명과 같게, 소문자·숫자·하이픈, 64자 이하, anthropic·claude 금지>
description: <결과물 한 줄>. <언제 쓰는가: 상황·파일 형식·사용자가 실제로 쓰는 한국어 표현 여러 개>. <쓰지 않는 경우와 담당 스킬명>. (1,024자 이하, 워크플로 단계는 쓰지 않는다)
metadata:
  author: humanist96
  version: <플러그인 버전과 같게>
  book-chapter: "<장 번호>"
# 필요할 때만:
# allowed-tools: <최소 권한. 무제한 Bash 대신 Bash(python *) 형태>
# compatibility: <ffmpeg, LibreOffice 등 환경 요구가 있을 때만, 500자 이하>
# argument-hint: "[인자 설명]"
# disable-model-invocation: true   # 사용자가 /호출할 때만 실행해야 하는 경우
---

<!--
작성 규칙 (계획서 §2.1, §3.5, §8)
- 본문 500줄·약 2,000단어 이하. 자동 컴팩션 후에는 앞 5,000토큰만 남으므로 핵심 규칙을 앞쪽에 둔다.
- Claude가 이미 아는 일반 지식(pandas 사용법 등)은 쓰지 않는다. 이 업무에서만 아는 판단 기준을 쓴다.
- "절대·반드시"를 남발하지 않고 이유를 한 줄 붙인다. 단, 보호 규칙(references/_shared/overrides.md §5)은 강제 표현을 유지한다.
- 환경 전용 경로(/mnt/user-data, present_files, ~/Desktop 등)를 쓰지 않는다. references/_shared/environment.md를 따른다.
- 긴 코드·스펙·플랫폼별 세부는 references/로 옮기고 아래 '참고'에서 언제 읽을지 적는다(한 단계 깊이까지만).
- 이 주석 블록은 지운다.
-->

# <스킬 제목>

<개요 1~2문장: 무엇을 만들고, 누구에게 왜 유용한가>

## 언제 쓰는가 / 쓰지 않는가

| 상황 | 이 스킬 | 다른 스킬 |
|------|:------:|-----------|
| <예: 엑셀 파일 정리·분석·취합> | ✅ | |
| <예: 셀 하나에 수식만 추가> | | xlsx 스킬 |

## 시작 전에

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 적용된 사용자 맞춤을 확인하고, 있으면 한 줄로 알린다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill <스킬명> --skill-dir ${CLAUDE_SKILL_DIR} --list
   ```

2. 출력 폴더를 정한다: `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/paths.py <스킬명> --create`
3. <필요한 정보가 없을 때만 묻는다. 기본값을 제안하고 한 번에 확인한다>

## 워크플로

복사해서 진행 상황을 체크한다.

```
- [ ] 1. <단계> — <왜 필요한가 한 줄>
- [ ] 2. <단계>
- [ ] 3. 품질 게이트 통과
- [ ] 4. 결과 전달
```

### 1. <단계 이름>

<판단 기준 중심. 정해진 명령이 있으면 그대로 적는다>

## 출력 규격

<파일 이름 규칙, 구조, 템플릿. 템플릿 파일은 overrides.py --resolve로 찾는다>

## 품질 게이트

결과를 전달하기 전에 검증기를 실행하고, 실패하면 고친 뒤 다시 실행한다. 통과하기 전에는 전달하지 않는다.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify_<무엇>.py <결과 파일>
```

| 검사 | 기준 |
|------|------|
| <예: 원본 행 수 보존> | <예: 정리 전후 행 수 차이 = 제거한 중복 수> |

## 건너뛰기 쉬운 단계 (합리화 표)

| 이런 생각이 들면 | 실제로는 | 그래서 |
|------------------|----------|--------|
| "사용자가 급하니 검증은 생략하자" | <검증 생략 시 실제로 생긴 문제> | 품질 게이트는 항상 실행한다 |
| <스킬별 반복 실패 지점> | | |

## 맞춤(오버라이드)

이 스킬이 받는 설정 키와 교체 가능한 파일은 README의 "커스터마이즈 포인트" 표에 있다.
규약 전체: `references/_shared/overrides.md`

## 참고

- `references/<파일>.md` — <언제 읽는가>
- 환경 규약: `references/_shared/environment.md`
