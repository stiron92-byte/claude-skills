---
max_turns: 20
timeout_seconds: 300
runs: 3
tags: [smoke]
allowed_tools: [Bash, Write, Edit, Read]
---
고객 명단을 정리해줘. 전화번호는 010-XXXX-XXXX, 날짜는 YYYY-MM-DD로 통일하고 중복은 빼서 clean/customers_정리.xlsx 로 저장해줘. 이상한 번호는 고치지 말고 따로 표시해줘.

```csv
이름,전화번호,가입일
홍길동,01012345678,2026/09/01
홍길동,01012345678,2026/09/01
김영희,010-777-888,2026.9.3
이철수,010 2222 3333,09/05/2026
```
