#!/usr/bin/env python3
"""R2: count_chars.py의 글자 수·X 가중치·해시태그·스레드 분할·한도 판정이 정확한지 확인한다.

기대값은 손으로 계산한 고정값이다. 양성 대조: 한도를 1자 넘긴 입력은 반드시 오류가 나야 하고, 한도 정확히 맞춘 입력은 통과해야 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repurpose_fixtures import SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
from count_chars import PLATFORMS, find_platform, measure, sections, split_tweets, x_weight  # noqa: E402

fails: list[str] = []


def eq(name, got, exp):
    if got != exp:
        fails.append(f"{name}: {got!r} ≠ {exp!r}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    # X 가중치: 한글 2, 영문 1, URL 23, 이모지 2
    eq("한글 140자", x_weight("가" * 140), 280)
    eq("영문 280자", x_weight("a" * 280), 280)
    eq("혼합+URL", x_weight("가나 abc https://example.com/very/long/path?x=1"), 2 + 2 + 1 + 3 + 1 + 23)
    eq("이모지", x_weight("🙂"), 2)
    eq("줄바꿈·숫자", x_weight("1/6\n가"), 3 + 1 + 2)
    # 스레드 분할과 한도
    thread = "1/3 " + "가" * 138 + "\n\n2/3 " + "가" * 139 + "\n\n3/3 끝 #태그 #둘"
    r = measure("x_thread", thread)
    eq("트윗 수", r["tweets"], 3)
    eq("트윗 가중치", r["tweet_weights"][:2], [4 + 276, 4 + 278])
    if not any("2번째 트윗" in p for p in r["problems"]) or any("1번째" in p for p in r["problems"]):
        fails.append(f"트윗 한도 판정(정확히 280은 통과, 282는 오류): {r['problems']}")
    eq("번호 없는 스레드 분할", len(split_tweets("첫째 문단\n\n둘째 문단\n\n셋째")), 3)
    # 인스타 해시태그·본문 한도
    tags = " ".join(f"#태그{i}" for i in range(31))
    r = measure("instagram", "본문\n" + tags)
    eq("해시태그 수", r["hashtags"], 31)
    if not any("해시태그 31개 > 한도 30개" in p for p in r["problems"]):
        fails.append(f"해시태그 31개 미검출: {r['problems']}")
    if measure("instagram", "가" * 2200)["problems"] or not measure("instagram", "가" * 2201)["problems"]:
        fails.append("인스타 2,200자 경계 판정 오류")
    if measure("threads", "가" * 500)["problems"] or not measure("threads", "가" * 501)["problems"]:
        fails.append("Threads 500자 경계 판정 오류")
    eq("HEX 색상은 해시태그 아님", measure("thumbnail", "주 색상 #FF5733, 강조 #1E90FF #엑셀")["hashtags"], 1)
    # 라벨 줄
    r = measure("seo_blog", "제목: 좋은 제목\n메타 디스크립션: 설명\n\n본문")
    eq("SEO 라벨", sorted(r["labels"]), ["meta", "title"])
    if r["problems"]:
        fails.append(f"SEO 라벨이 있는데 required 오류: {r['problems']}")
    if not measure("seo_blog", "본문만")["problems"]:
        fails.append("SEO 제목·메타 없음 미검출")
    nl = measure("newsletter", "제목: " + "가" * 51 + "\n프리헤더: 짧다\n\n본문")
    if not any("subject 51자" in n for n in nl["notes"]):
        fails.append(f"뉴스레터 제목 51자 권장 초과 미검출: {nl['notes']}")
    # 제목 인식
    for head, pid in [("X (Twitter) 스레드", "x_thread"), ("Instagram 캡션", "instagram"), ("[네이버 블로그]", "naver_blog"),
                      ("SEO 블로그 포스트", "seo_blog"), ("Threads 게시물", "threads"), ("LinkedIn 게시물", "linkedin"),
                      ("뉴스레터 본문 (Substack/스티비 등)", "newsletter"), ("YouTube Shorts 스크립트", "yt_shorts"), ("요약 표", None)]:
        eq(f"제목 인식 {head}", find_platform(head), pid)
    eq("섹션 분할", [h for h, _ in sections("# 제목\n## A\n본문\n## B\n본문")], ["A", "B"])
    # 블로그 본문의 '##' 소제목은 플랫폼 섹션으로 보지 않고 본문에 붙인다(평가 중 발견: 소제목에 '뉴스레터'가 들어간 경우)
    md = "## SEO 블로그 포스트\n도입\n## 뉴스레터 구독자를 늘린 3가지 변화\n본론 끝 문장\n## X 스레드\n1/5 훅\n## 요약\n| 표 |"
    secs = sections(md)
    eq("소제목 병합", [h for h, _ in secs], ["SEO 블로그 포스트", "X 스레드", "요약"])
    if "본론 끝 문장" not in secs[0][1]:
        fails.append("블로그 소제목 아래 본문이 블로그 섹션에서 빠졌다")
    eq("소제목은 플랫폼 아님", find_platform("뉴스레터 구독자를 늘린 3가지 변화"), None)
    eq("플랫폼 수", len(PLATFORMS), 14)
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"COUNT CHARS FAILED ({len(fails)})")
        return 1
    print("COUNT CHARS OK — X 가중치·스레드 분할·경계값(280/2,200/500/해시태그 30)·라벨·플랫폼 제목 인식 확인")
    return 0


if __name__ == "__main__":
    sys.exit(main())
