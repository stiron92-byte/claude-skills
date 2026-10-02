#!/usr/bin/env python3
"""content-repurpose 실습 원본(자체 작성 유튜브 대본)과 정답표를 만든다. 매번 같은 결과가 나온다.

왜
- v1.6.1 8장 폴더의 유튜브 녹취(Claude Code 유출 에피소드)는 제3자 채널의 발언을 옮긴 것이라 실습 배포에 권리 문제가 있다.
- 리퍼포징의 핵심 실패는 '원본에 없는 숫자·주장 지어내기'다. 그것을 채점하려면 숫자와 단서가 분명한 원본과 정답표가 필요하다.

원본에 일부러 넣은 것
- 숫자 12개(구독자·오픈율·답장률·기간·시간). 결과물의 숫자는 이 안에서만 나와야 한다
- 단서: "제 경우이고 분야마다 다르다", "아직 유료화는 안 했다(광고 제안 2건 거절)" — 수익·보장 표현을 지어내기 쉬운 지점
- 핵심 메시지 3개와 다음 영상 예고(CTA)

정답표에는 책 8장 실습 8-1(감사) 목록의 집계 정답도 함께 둔다(평가 채점용).

사용법: python tools/dev/make_repurpose_practice.py [--check]
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/content-repurpose/inputs"
SOURCE_NAME = "원본_유튜브대본_뉴스레터1000명.md"

SOURCE = """# 퇴근 후 1시간으로 뉴스레터 구독자 1,000명 모은 방법

(유튜브 영상 대본 · 약 4분)

안녕하세요. 오늘은 제가 퇴근 후 하루 1시간만 써서 뉴스레터 구독자를 1,000명까지 모은 과정을 솔직하게 이야기해 보려고 합니다.

저는 평범한 회사원이고, 2025년 1월에 '엑셀 한 스푼'이라는 뉴스레터를 시작했습니다. 처음 3개월 동안 모인 구독자는 87명이었어요. 솔직히 그때는 그만둘까 고민도 많이 했습니다. 그런데 시작하고 6개월째 되던 달에 구독자 1,000명을 넘겼습니다. 그 사이에 바꾼 것은 딱 세 가지예요.

첫 번째, 주제를 아주 좁혔습니다. 처음에는 '직장인 업무 팁'이라는 넓은 주제로 썼는데, 독자가 왜 이걸 읽어야 하는지 분명하지 않았어요. 그래서 '매주 엑셀 함수 하나'로 좁혔습니다. 한 호에 함수 하나, 예제 파일 하나. 이렇게 바꾸고 나서 오픈율이 평균 48%까지 올랐습니다. 처음에는 31% 정도였거든요.

두 번째, 발행 요일과 시간을 고정했습니다. 매주 화요일 오전 7시에 보냅니다. 출근길 지하철에서 읽기 좋은 시간이라서요. 한 번도 빠지지 않고 지키는 게 생각보다 중요했습니다. 독자분들이 "화요일 아침이면 기다린다"는 답장을 보내 주시기 시작했어요.

세 번째, 독자 질문을 다음 호 주제로 썼습니다. 매 호 마지막에 "요즘 엑셀에서 막히는 게 뭐예요?"라고 물어봤어요. 답장률이 평균 12% 정도 나왔고, 그 질문들이 그대로 다음 주제가 됐습니다. 독자는 자기 질문이 소개되니까 친구에게 공유하고, 그게 구독자 증가로 이어졌습니다.

시간은 어떻게 썼냐면요, 글쓰기에 40분, 예제 파일 만들고 편집하는 데 20분. 이렇게 매일이 아니라 일주일에 하루, 1시간입니다. 나머지 날은 독자 답장만 읽어요.

오해하실까 봐 말씀드리면, 아직 유료화는 하지 않았습니다. 광고 제안이 2건 들어왔는데, 지금은 구독자와 신뢰를 쌓는 게 먼저라고 생각해서 정중히 거절했어요. 그리고 이건 제 경우입니다. 분야마다, 사람마다 속도는 다를 수 있어요. 다만 주제를 좁히고, 약속한 시간에 보내고, 독자와 대화하는 것. 이 세 가지는 어떤 분야든 통한다고 생각합니다.

다음 영상에서는 첫 호를 실제로 어떻게 썼는지, 제목 짓는 법부터 보여 드릴게요. 도움이 됐다면 구독 부탁드립니다. 감사합니다.
"""

KEY = {
    "source": SOURCE_NAME,
    "title": "퇴근 후 1시간으로 뉴스레터 구독자 1,000명 모은 방법",
    "core_messages": [
        {"key": "주제를 좁힌다", "any": ["좁", "함수 하나"]},
        {"key": "발행 요일·시간 고정", "any": ["화요일", "고정"]},
        {"key": "독자 질문을 다음 주제로", "any": ["질문", "답장"]},
    ],
    "numbers": ["1,000명", "2025년 1월", "3개월", "87명", "6개월", "48%", "31%", "화요일 오전 7시", "12%", "40분", "20분", "1시간", "2건"],
    "must_not": ["유료화 수익을 냈다는 주장", "누구나·반드시 1,000명을 모을 수 있다는 보장", "원본에 없는 수치(매출, 구독자 증가율 등)"],
    "caveats": ["아직 유료화하지 않음(광고 제안 2건 거절)", "제 경우이고 분야마다 다를 수 있음"],
    "cta": "다음 영상: 첫 호 쓰는 법·제목 짓는 법",
}

# 책 8장 실습 8-1 목록(프롬프트 원문)의 집계 정답 — 오늘(평가일 2026-10-02) 기준
AUDIT_8_1 = {
    "items": 10,
    "categories": {"AI 도구": 5, "AI 활용": 1, "커리어": 1, "AI 뉴스": 1, "AI 전망": 1, "AI 개념": 1},
    "top_category": "AI 도구",
    "top_share": 0.5,
    "date_range": ["2024-06", "2025-04"],
    "older_than_6_months_as_of_2026_10": 10,
    "overlap_groups_by_words": [["ChatGPT vs Claude 비교", "Claude 3.5 Sonnet 리뷰", "AI 코딩 도구 비교"]],
    "overlap_note": "제목 단어로 묶이는 것은 위 3개. 'Cursor IDE 사용법'도 AI 코딩 도구 계열이라 함께 묶을지는 판단 영역",
    "time_sensitive": ["GPT-4o 업데이트 정리", "Claude 3.5 Sonnet 리뷰", "2025 AI 트렌드 예측"],
    "months_since_last_as_of_2026_10": 18,
    "channels": ["블로그", "유튜브"],
    "note": "목록에 조회수·성과 데이터가 없다. 성과 수치를 지어내면 안 된다. 2025-04 이후 발행이 없다(약 18개월 공백).",
}

GAP_8_2 = {
    "mine_partial": True, "competitor_partial": True,
    "topic_gaps": ["AI 실전 활용(부동산 투자 분석 등 도메인 적용)", "비개발자 자동화 워크플로", "뉴스레터 자동 발행(실습형)"],
    "overlap": ["AI 도구 비교(경쟁: Claude Code vs Devin vs Cursor, 내 쪽: ChatGPT vs Claude, Cursor IDE)"],
    "format_gaps": ["실습형·튜토리얼 형식"],
    "note": "두 목록 모두 '(생략)'이 있어 일부만 주어졌다. 분석이 일부 목록 기준임을 밝혀야 한다. 검색량 등 수치를 사실처럼 지어내면 안 된다.",
}


def write(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / SOURCE_NAME).write_text(SOURCE, encoding="utf-8")
    key = {"generated_by": "tools/dev/make_repurpose_practice.py", "repurpose": KEY, "audit_8_1": AUDIT_8_1, "gap_8_2": GAP_8_2}
    (target / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as td:
            write(Path(td))
            diff = [n for n in (SOURCE_NAME, "answer_key.json") if (Path(td) / n).read_bytes() != (OUT / n).read_bytes()]
        print("DIFF: " + ", ".join(diff) if diff else "REPRODUCIBLE")
        return 1 if diff else 0
    write(OUT)
    print(f"written: {OUT / SOURCE_NAME} ({len(SOURCE)}자), answer_key.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
