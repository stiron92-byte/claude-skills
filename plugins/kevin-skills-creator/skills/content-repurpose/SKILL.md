---
name: content-repurpose
description: 원본 콘텐츠(유튜브 대본, 강의·발표 원고, 회의록, 블로그 글, 뉴스레터)를 플랫폼별 게시용 글로 바꾼다. SEO·네이버 블로그, 브런치, Medium, X 스레드, LinkedIn, Instagram, Threads, Facebook, 뉴스레터, 쇼츠·틱톡 대본, Pinterest, 썸네일 가이드 14종을 지원하고, 글자 수(X 가중치 포함)·형식·원본에 없는 숫자를 스크립트로 검사한다. 콘텐츠 목록의 감사(주제 분포·오래된 글·중복)와 경쟁 채널 대비 갭 분석도 한다. "이 대본 블로그랑 인스타로 바꿔줘", "유튜브 대본을 X 스레드로", "강의 내용 링크드인 글로", "뉴스레터로 바꿔줘", "원소스 멀티유즈", "내 블로그 콘텐츠 감사해줘", "경쟁 채널이랑 콘텐츠 갭 분석"처럼 이미 있는 콘텐츠를 다른 형태로 바꾸거나 콘텐츠 목록을 분석할 때 사용한다. 쇼츠 영상 파일(mp4) 제작은 generate-shorts, 새 주제 조사·트렌드 리서치는 content-research, 발표 PPT는 doc-automation이 맡고, 원본 없이 처음부터 쓰는 글에는 쓰지 않는다.
metadata:
  author: humanist96
  version: 2.0.0-alpha.1
  book-chapter: "8"
---

# 콘텐츠 리퍼포징

리퍼포징 결과가 틀리는 지점은 대개 세 곳이다. 플랫폼 한도를 넘겨 잘리고, 원본에 없는 숫자나 성과를 그럴듯하게 지어내고, "아래는 ~입니다" 같은 안내문과 자리표시가 남아 바로 올릴 수 없다.
그래서 이 스킬은 원본의 핵심 메시지와 숫자를 먼저 브리프로 정리하고, 선택한 플랫폼의 스펙만 읽어 쓴 뒤, `check_repurpose.py`로 한도·형식·숫자 출처를 검사하고 전달한다.

## 언제 쓰는가 / 쓰지 않는가

| 상황 | 이 스킬 | 다른 스킬 |
|------|:------:|-----------|
| 대본·원고·글 → 플랫폼별 게시글 | ✅ 변환 | |
| 콘텐츠 목록의 주제 분포·오래된 글·중복 점검 | ✅ 감사 | |
| 내 목록 vs 경쟁 목록 비교 | ✅ 갭 분석 | |
| 쇼츠·틱톡 **대본** | ✅ | |
| 쇼츠 **영상 파일**(자르기·자막) | | generate-shorts |
| 새 주제·트렌드 조사 | | content-research(결과를 이 스킬로 넘김) |
| 발표 PPT | | doc-automation |

## 시작 전에

> 명령의 `${CLAUDE_SKILL_DIR}`는 Claude Code가 이 스킬 폴더 경로로 바꿔 준다. 바뀌지 않은 채 보이면 이 SKILL.md가 있는 폴더 경로를 넣는다.

1. 사용자 맞춤을 확인한다. 기본 플랫폼 묶음·톤, 브랜드 보이스, 금칙어가 있으면 "적용된 맞춤: 브랜드 보이스, 기본 플랫폼 3종"처럼 한 줄로 알린다.

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill content-repurpose --skill-dir ${CLAUDE_SKILL_DIR} --list
   python ${CLAUDE_SKILL_DIR}/scripts/_vendor/overrides.py --skill content-repurpose --skill-dir ${CLAUDE_SKILL_DIR} --settings
   ```

2. 작업 폴더를 정한다: `python ${CLAUDE_SKILL_DIR}/scripts/_vendor/paths.py content-repurpose --create` → 이하 `<W>`
3. 모드를 정한다: 원본을 바꾸는 요청은 변환, 콘텐츠 목록을 주며 점검을 원하면 감사, 경쟁 목록이 함께 오면 갭 분석. 감사·갭 분석은 `references/audit-gap.md`를 따른다.

## 워크플로(변환)

```
- [ ] 1. 원본 확보 — <W>/source.md로 저장
- [ ] 2. 브리프 — 핵심 메시지 3개(키워드 포함), 숫자, 단서, 톤, 언어 → <W>/brief.json
- [ ] 3. 플랫폼 정하기 — 요청 → 맞춤 기본값 → 한 번 확인(못 물으면 기본 3종)
- [ ] 4. 플랫폼별 작성 — 선택한 플랫폼의 references/platforms/<id>.md만 읽는다
- [ ] 5. 검증 — check_repurpose 통과
- [ ] 6. 저장·전달 — <W>/repurposed-<주제>-<날짜>.md, 플랫폼별 글자 수 표
```

### 1. 원본 확보

붙여 넣은 텍스트는 그대로, 파일은 읽어서, 웹 글은 WebFetch로 가져와 `<W>/source.md`에 저장한다(웹 글은 첫 줄에 URL과 가져온 시각).
유튜브 링크만 있고 대본이 없으면 자막·대본을 붙여 달라고 요청한다. 영상 내용을 추측해 쓰지 않는다.

### 2. 브리프

원본을 끝까지 읽고 `<W>/brief.json`을 쓴다.

```json
{"core_messages": [{"text": "주제를 좁힌다", "keywords": ["좁", "함수 하나"]}],
 "numbers": ["1,000명", "48%"], "caveats": ["아직 유료화 안 함"], "tone": "친근", "language": "ko", "audience": "직장인"}
```

- 핵심 메시지는 3개 안팎. `keywords`는 결과물에 그 메시지가 들어갔는지 확인할 단어다.
- `caveats`는 원본의 단서·한계(개인 경험, 결과 보장 없음, 아직 안 한 일)다. 결과물에서 지우지 않는다.
- 톤·언어가 요청에 없으면 원본의 톤을 따르고 언어는 원본 언어를 따른다(맞춤 settings `tone`·`language`가 있으면 그것).

### 3. 플랫폼 정하기

| 순서 | 출처 |
|:---:|------|
| 1 | 요청에 적힌 플랫폼("블로그랑 인스타") |
| 2 | 맞춤 settings `default_platforms` |
| 3 | 물을 수 있으면 한 번 묻는다: "SEO 블로그·X 스레드·Instagram 3종으로 만들까요? 다른 플랫폼이 필요하면 골라 주세요" |
| 4 | 물을 수 없으면 SEO 블로그·X 스레드·Instagram으로 만들고 6단계에서 알린다 |

14종 전부를 임의로 만들지 않는다. 플랫폼 id와 섹션 제목은 `references/platforms/<id>.md` 머리말에 있다.

### 4. 플랫폼별 작성

- 선택한 플랫폼마다 `references/platforms/<id>.md`(스펙·구조·예시)를 읽고 쓴다. 첫 문장은 `references/hooks.md`의 공식 중 원본 사실로 지킬 수 있는 것을 고른다.
- 브랜드 보이스·금칙어가 맞춤에 있으면 `overrides.py --resolve references/brand-voice.md`로 찾아 먼저 읽는다.
- 결과 파일은 플랫폼마다 `## <플랫폼 섹션 제목>` 하나. 섹션 안은 붙여 넣기만 하면 게시되는 완성본이다: 자리표시·작성 메모("톤:")·코드 블록·"아래는 ~입니다" 안내문을 넣지 않는다.
- 숫자는 원본에 있는 값만 쓴다. 합계·비율처럼 계산한 값도 원본에 없으면 쓰지 않는다. 원본에 없는 수익·성과·보장 표현을 만들지 않는다.
- 한도는 `scripts/count_chars.py`로 센다. X는 한글·이모지를 2로 세는 가중치 280이다(한글만이면 140자).

```bash
python ${CLAUDE_SKILL_DIR}/scripts/count_chars.py <W>/repurposed.md
```

### 5. 검증

```bash
python ${CLAUDE_SKILL_DIR}/scripts/check_repurpose.py <W>/repurposed.md --source <W>/source.md --platforms x_thread,instagram,seo_blog --brief <W>/brief.json
```

`REPURPOSE VERIFY OK`가 나올 때까지 고친다. 오류를 피하려고 숫자나 핵심 메시지를 지우지 않는다. 원본 값으로 바꾸거나 문장을 다시 쓴다.
경고(권장 분량·해시태그 수·일부 핵심 메시지 누락)는 플랫폼 특성상 의도한 것이면 두고, 아니면 고친다.

### 6. 저장·전달

1. 결과 파일 경로. 플랫폼이 하나뿐이고 짧으면 채팅에 본문도 붙인다
2. 표: 플랫폼 · 글자 수(X는 트윗 수·최대 가중치) · 해시태그 수 · 첫 문장(훅)
3. 가정한 것(플랫폼·톤·언어 기본값)과 검증 결과 한 줄, 남긴 경고
4. 원본에서 일부러 뺀 내용이 있으면 그 이유(예: 숏폼 분량 때문에 세 번째 메시지 생략)

결과물에 스킬 소개·홍보 문구를 넣지 않는다.

## 건너뛰기 쉬운 단계 (합리화 표)

| 이런 생각이 들면 | 실제로는 | 그래서 |
|------------------|----------|--------|
| "글자 수는 대충 맞다" | 한글 트윗은 140자에서 잘린다 | count_chars로 센다 |
| "숫자를 키우면 더 끌린다" | 원본과 다른 숫자는 신뢰를 잃고 문제가 된다 | 원본 값만, check_repurpose 숫자 검사 |
| "단서는 SNS에선 빼도 된다" | '개인 경험'이 '누구나 가능'으로 바뀐다 | caveats를 짧게라도 남긴다 |
| "플랫폼을 다 만들어 주면 친절하다" | 쓰지 않을 글 13개는 검토 부담이다 | 요청·기본값의 플랫폼만 |
| "스펙은 기억하고 있다" | 플랫폼마다 한도·형식이 다르다 | 선택한 플랫폼 파일을 읽는다 |
| "감사 리포트 숫자는 눈으로 세면 된다" | 비율·경과 개월은 틀리기 쉽다 | content_inventory로 센다 |

## 맞춤(오버라이드)

기본 플랫폼 묶음·톤·언어(`settings.yaml`), 브랜드 보이스(`references/brand-voice.md`), 금칙어·해시태그 정책(`references/banned-words.md`), 사내 채널 스펙(`references/platforms/<새 id>.md`)을 더하거나 바꿀 수 있다.
목록은 README의 "커스터마이즈 포인트", 규약은 `references/_shared/overrides.md`.

## 참고

- `references/platforms/<id>.md` — 플랫폼 14종의 한도·구조·예시(4단계, 선택한 것만)
- `references/hooks.md` — 첫 문장·CTA 공식과 피할 표현(4단계)
- `references/audit-gap.md` — 감사·갭 분석 절차와 리포트 구성
- `examples/example-usage.md` — 원본 대본과 변환 결과 예시
- 환경 규약: `references/_shared/environment.md`
