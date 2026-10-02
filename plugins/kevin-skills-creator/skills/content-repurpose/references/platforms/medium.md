# Medium 아티클 (`medium`)

결과 파일에서 이 플랫폼 섹션 제목은 `## Medium 아티클`으로 쓴다(`scripts/count_chars.py`가 제목으로 플랫폼을 알아본다).
'실제 한도'는 넘으면 게시가 막히거나 잘리는 값이라 오류, '권장'은 경고다.

## 스펙

| 항목 | 한도 | 종류 |
|------|------|------|
| 제목 | 60자 이내(영문 기준) | 권장 |
| 본문 | 영문 1,500~3,000단어 / 한글 2,000~4,000자 | 권장 |

결과 맨 위에 `제목:`, `서브타이틀:`, `태그:`(5개 이내) 줄. 구조: 훅 → 문제 정의 → 소제목별 본론 → 결론·CTA. 기술 글은 코드 블록을 본문 안에 써도 된다(결과 전체를 감싸지는 않는다).

## 예시

예시는 `examples/example-usage.md`의 원본(1인 개발자 수익 대본)을 바꾼 것이다. 숫자는 모두 원본에 있는 값이다.

제목: Three Income Streams, Added One at a Time
서브타이틀: How a solo developer reached about 9 million won a month without starting everything at once
태그: Indie Hacking, SaaS, Freelancing, Side Project, Developer

Most solo developers try to build an app, a course, and a client list in the same quarter. I added them over three years.
