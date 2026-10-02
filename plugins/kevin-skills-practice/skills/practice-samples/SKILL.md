---
name: practice-samples
description: 책 『압도적 스킬로 바로 쓰는 클로드 코워크×AI 자동화』와 강의의 실습 샘플 파일(환율 PDF, 가상 회사 문서, HWPX 결재 양식, 주간 매출 CSV, 엑셀 실습 파일, 회의 녹음, 쇼츠·나레이션 오프라인 데모)을 찾아 사용자 작업 폴더로 복사한다. "실습 파일 복사해줘", "2장 실습 샘플 찾아줘", "플러그인에 들어 있는 예제 파일", "claude skills book 플러그인에 실습 PDF가 있을 거야", "회의록 샘플 녹음", "완성 예시 보여줘"처럼 실습용 입력이나 완성 예시를 찾는 요청에 사용한다. 실제 업무 파일을 처리하는 요청에는 쓰지 않는다(각 업무 스킬이 담당).
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
---

# 실습 샘플 복사

실습 샘플은 플러그인 설치 폴더 안에 있다. 사용자가 직접 찾기 어렵고, 그 자리에서 수정하면 플러그인 업데이트 때 사라진다.
그래서 항상 사용자의 작업 폴더로 **복사**한 뒤 실습한다.

## 절차

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 어떤 실습인지 파악한다. 장 번호, 스킬 이름, 파일 설명 중 하나라도 있으면 된다.
2. 세트 목록을 본다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/copy_samples.py --list
   python ${CLAUDE_SKILL_DIR}/scripts/copy_samples.py --list --chapter 2
   ```

3. 해당 세트를 복사한다. 사용자가 위치를 말하지 않았으면 현재 작업 폴더에 복사한다. 세트마다 정해진 하위 폴더(예: `2장-기업PPT/`)가 만들어진다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/copy_samples.py --set doc-company-ppt
   python ${CLAUDE_SKILL_DIR}/scripts/copy_samples.py --chapter 4          # 4장 입력 세트 전부
   python ${CLAUDE_SKILL_DIR}/scripts/copy_samples.py --chapter 2 --include-results   # 완성 예시 포함
   ```

4. 결과 JSON의 `copied`, `skipped_existing`, `missing`을 사용자에게 짧게 알린다. 복사된 폴더 경로를 링크로 준다.
5. 출력 끝의 `[주의]` 줄(권리 안내)이 있으면 그대로 전한다.

## 세트 종류

| kind | 의미 | 언제 쓰나 |
|------|------|-----------|
| `input` | 실습 입력 파일 | 실습을 시작할 때 |
| `reference-output` | 완성 예시 | 결과를 비교하거나 실습을 건너뛸 때. 사용자가 원할 때만 복사 |
| `offline-demo` | 네트워크 없이 이어서 진행할 중간 결과 | 강의장에서 YouTube·Gemini 접속이 막혔을 때 |

## 지켜야 할 것

- 이미 있는 파일은 덮어쓰지 않는다. 스크립트가 건너뛰고 `skipped_existing`에 적는다. 사용자가 이미 고친 실습 파일일 수 있기 때문이다.
- 플러그인 폴더 안의 샘플을 직접 열어 수정하지 않는다.
- 복사가 끝나면 해당 업무 스킬로 실습을 이어 가도록 다음 요청 예시를 한 줄 제안한다. 예: "복사한 PDF로 과장님 보고용 PPT 만들어줘".

## 참고

- 전체 목록과 권리 메모: `samples/catalog.json`
- 강의 전 환경 점검은 `doctor` 스킬을 쓴다.
