#!/usr/bin/env python3
"""플랫폼별 글자 수·해시태그·스레드 길이 계산. 눈대중 대신 이 스크립트로 센다.

한도는 두 종류다.
- hard: 플랫폼이 실제로 막는 한도(넘으면 게시 불가·잘림). 넘으면 오류
- guide: 이 스킬이 권하는 분량(읽히는 길이). 벗어나면 경고
글자 수는 줄바꿈·공백·이모지를 포함한 유니코드 문자 수다. X(트위터)만 가중치를 쓴다:
한글·한자·일본어·이모지는 2, 영문·숫자·기본 기호는 1, URL은 길이와 관계없이 23. 한도 280(한글만 쓰면 140자).

사용법
  python count_chars.py <결과.md> [--json]          # '## 플랫폼명' 섹션마다 계산
  python count_chars.py --text "문장" --platform x   # 한 문장만
라이브러리: from count_chars import PLATFORMS, measure, x_weight, find_platform
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# id: (표시 이름, 제목 별칭, 한도) — 한도 값은 references/platforms/<id>.md와 같아야 한다
PLATFORMS: dict[str, dict] = {
    "seo_blog": {"name": "SEO 블로그 포스트", "aliases": ["seo 블로그", "seo blog", "블로그 포스트", "seo"],
                 "guide": {"body": (1500, 2500), "title": 50, "meta": 155}},
    "naver_blog": {"name": "네이버 블로그", "aliases": ["네이버 블로그", "naver"], "guide": {"body": (1500, 3000), "title": 40}},
    "brunch": {"name": "브런치 글", "aliases": ["브런치", "brunch"], "guide": {"body": (2000, 4000)}},
    "medium": {"name": "Medium 아티클", "aliases": ["medium", "미디엄"], "guide": {"body": (2000, 4000), "title": 60}},
    "x_thread": {"name": "X 스레드", "aliases": ["x (twitter)", "x 스레드", "트위터", "twitter", "x thread", "x(트위터)"],
                 "hard": {"tweet_weight": 280}, "guide": {"tweets": (5, 10), "hashtags_last": (2, 3)}},
    "linkedin": {"name": "LinkedIn 게시물", "aliases": ["linkedin", "링크드인"], "hard": {"body": 3000},
                 "guide": {"body": (0, 1300), "hashtags": (3, 5), "hook_lines": 3}},
    "instagram": {"name": "Instagram 캡션", "aliases": ["instagram", "인스타그램", "인스타"], "hard": {"body": 2200, "hashtags": 30},
                  "guide": {"hashtags": (20, 30)}},
    "threads": {"name": "Threads 게시물", "aliases": ["threads", "스레드 게시물", "쓰레드"], "hard": {"body": 500}},
    "facebook": {"name": "Facebook 게시물", "aliases": ["facebook", "페이스북"], "guide": {"body": (0, 500)}},
    "newsletter": {"name": "뉴스레터", "aliases": ["뉴스레터", "newsletter", "substack", "스티비"],
                   "guide": {"subject": 50, "preheader": 80}},
    "yt_shorts": {"name": "YouTube Shorts 스크립트", "aliases": ["shorts", "쇼츠", "youtube shorts"], "guide": {"body": (150, 300)}},
    "tiktok": {"name": "TikTok 스크립트", "aliases": ["tiktok", "틱톡"], "guide": {"body": (150, 300)}},
    "pinterest": {"name": "Pinterest 핀", "aliases": ["pinterest", "핀터레스트"], "hard": {"title": 100, "body": 500}},
    "thumbnail": {"name": "썸네일·비주얼 가이드", "aliases": ["썸네일", "thumbnail", "비주얼 가이드"], "guide": {"thumb_text": (4, 8)}},
}

URL = re.compile(r"https?://\S+")
HASHTAG = re.compile(r"(?<![\w#])#(?![0-9A-Fa-f]{6}(?![0-9A-Za-z가-힣]))[^\s#.,!?()\[\]{}]+")  # HEX 색상(#FF5733)은 제외
TWEET_MARK = re.compile(r"^\s*(?:\*\*)?(\d{1,2})\s*/\s*(\d{1,2})(?:\*\*)?[.)]?\s*", re.M)
LABEL = re.compile(r"^\s*(?:\*\*)?(제목|메타 ?디스크립션|메타 설명|키워드|주요 키워드|subject(?: line)?|제목줄|프리헤더|preheader|서브타이틀|부제|태그|보드|설명|핀 제목)(?:\*\*)?\s*[:：]\s*(.+)$", re.I | re.M)


GENERIC_WORDS = {"본문", "게시물", "게시글", "포스트", "포스팅", "캡션", "스레드", "글", "아티클", "스크립트", "대본", "가이드", "버전", "핀",
                 "설명", "비주얼", "영문", "한국어", "초안", "최종", "용", "블로그", "메일", "이메일", "캐러셀", "포함", "결과", "콘텐츠",
                 "post", "caption", "thread", "article", "script", "copy", "version", "guide", "(twitter)", "x", "twitter"}


def find_platform(heading: str) -> str | None:
    h = heading.lower().replace("[", "").replace("]", "").strip()
    best = None
    for pid, p in PLATFORMS.items():
        for a in p["aliases"]:
            if a in h and (best is None or len(a) > best[1]):
                best = (pid, len(a), a)
    if not best:
        return None
    # 플랫폼 이름 외의 단어가 일반 단어뿐일 때만 플랫폼 제목이다
    # ("뉴스레터 본문" O, "뉴스레터 구독자를 늘린 3가지 변화" X — 블로그 소제목)
    rest = h
    for a in sorted(PLATFORMS[best[0]]["aliases"], key=len, reverse=True):  # 같은 플랫폼의 별칭은 모두 지운다
        rest = rest.replace(a, " ")
    rest = re.sub(r"\(.*?\)|（.*?）", " ", rest)
    words = [w for w in re.split(r"[\s·/,|:\-–—]+", rest) if w and not re.fullmatch(r"\d+[.)]?", w)]
    if any(w not in GENERIC_WORDS for w in words):
        return None
    return best[0]


def x_weight(text: str) -> int:
    """X(트위터) 가중치 글자 수(twitter-text v3 규칙 단순화).
    URL은 23. 이모지 결합 시퀀스(👨‍👩‍👧)는 코드 포인트마다 2로 세므로 실제보다 크게 나온다(안전한 쪽으로 틀림)."""
    w = 23 * len(URL.findall(text))
    for ch in URL.sub("", text):
        cp = ord(ch)
        if cp <= 0x10FF or 0x2000 <= cp <= 0x200D or 0x2010 <= cp <= 0x201F or 0x2032 <= cp <= 0x2037:
            w += 1
        else:
            w += 2
    return w


def split_tweets(body: str) -> list[str]:
    marks = list(TWEET_MARK.finditer(body))
    if len(marks) < 2:
        parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        return parts
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out.append(body[m.start():end].strip())
    return out


def labeled(body: str) -> dict[str, str]:
    out = {}
    for m in LABEL.finditer(body):
        k = m.group(1).lower().replace(" ", "")
        k = {"메타디스크립션": "meta", "메타설명": "meta", "subject": "subject", "subjectline": "subject", "제목줄": "subject",
             "프리헤더": "preheader", "preheader": "preheader", "핀제목": "title", "제목": "title"}.get(k, k)
        out.setdefault(k, m.group(2).strip().strip("*").strip())
    return out


def measure(pid: str, body: str) -> dict:
    """한 플랫폼 섹션의 수치. 위반은 problems(hard)·notes(guide)에 담는다."""
    spec = PLATFORMS[pid]
    hard, guide = spec.get("hard", {}), spec.get("guide", {})
    text = body.strip()
    res: dict = {"platform": pid, "chars": len(text), "hashtags": len(HASHTAG.findall(text)), "problems": [], "notes": []}
    lab = labeled(text)
    if pid == "newsletter" and "subject" not in lab and "title" in lab:
        lab["subject"] = lab["title"]  # 뉴스레터의 '제목'은 메일 제목(subject line)
    res["labels"] = lab
    if pid == "x_thread":
        tweets = split_tweets(text)
        weights = [x_weight(t) for t in tweets]
        res.update(tweets=len(tweets), tweet_weights=weights)
        for i, w in enumerate(weights, 1):
            if w > hard["tweet_weight"]:
                res["problems"].append(f"{i}번째 트윗 {w}/280(가중치) 초과")
        lo, hi = guide["tweets"]
        if not lo <= len(tweets) <= hi:
            res["notes"].append(f"트윗 {len(tweets)}개(권장 {lo}~{hi})")
        if tweets:
            ht = len(HASHTAG.findall(tweets[-1]))
            lo, hi = guide["hashtags_last"]
            if not lo <= ht <= hi:
                res["notes"].append(f"마지막 트윗 해시태그 {ht}개(권장 {lo}~{hi})")
        return res
    if "body" in hard and len(text) > hard["body"]:
        res["problems"].append(f"본문 {len(text)}자 > 한도 {hard['body']}자")
    if "hashtags" in hard and res["hashtags"] > hard["hashtags"]:
        res["problems"].append(f"해시태그 {res['hashtags']}개 > 한도 {hard['hashtags']}개")
    if "title" in hard and lab.get("title") and len(lab["title"]) > hard["title"]:
        res["problems"].append(f"제목 {len(lab['title'])}자 > 한도 {hard['title']}자")
    if "body" in guide:
        lo, hi = guide["body"]
        if not lo <= len(text) <= hi:
            res["notes"].append(f"분량 {len(text)}자(권장 {lo}~{hi}자)")
    if "hashtags" in guide:
        lo, hi = guide["hashtags"]
        if not lo <= res["hashtags"] <= hi:
            res["notes"].append(f"해시태그 {res['hashtags']}개(권장 {lo}~{hi}개)")
    for k in ("title", "meta", "subject", "preheader"):
        if k in guide and lab.get(k) and len(lab[k]) > guide[k]:
            res["notes"].append(f"{k} {len(lab[k])}자(권장 {guide[k]}자 이내)")
    if pid == "newsletter" and "subject" not in lab:
        res["problems"].append("뉴스레터 제목(subject line) 줄이 없다 — '제목: …' 형식으로 쓴다")
    if pid == "seo_blog":
        for k in ("title", "meta"):
            if k not in lab:
                res["problems"].append(f"SEO 블로그 '{'제목' if k == 'title' else '메타 디스크립션'}' 줄이 없다")
    return res


TERMINATOR = re.compile(r"(요약|정리 표|summary|참고|메모|확인|가정|검증|notes?)", re.I)


def sections(md: str) -> list[tuple[str, str]]:
    """'## 제목' 단위로 나눈다.

    플랫폼이 아닌 '## 제목'은 블로그 본문의 소제목일 수 있으므로 앞 플랫폼 섹션에 이어 붙인다.
    단, '요약'·'참고'·'가정'처럼 결과물 밖의 안내로 보이는 제목에서는 섹션을 끝내고 따로 돌려준다.
    """
    out: list[list] = []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            head = m.group(1)
            if find_platform(head) or not out or not find_platform(out[-1][0]) or TERMINATOR.search(head):
                out.append([head, []])
                continue
            out[-1][1].append(line)  # 블로그 소제목 등은 본문으로
        elif out:
            out[-1][1].append(line)
    return [(h, "\n".join(b)) for h, b in out]


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="플랫폼별 글자 수 계산")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--text")
    ap.add_argument("--platform")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = []
    if a.text is not None:
        pid = a.platform or "threads"
        rows.append(("(입력)", measure(pid, a.text)))
    else:
        if not a.file or not Path(a.file).is_file():
            print("오류: 결과 파일 경로가 필요합니다")
            return 2
        for head, body in sections(Path(a.file).read_text(encoding="utf-8")):
            pid = find_platform(head)
            if pid:
                rows.append((head, measure(pid, body)))
    if a.json:
        print(json.dumps([r for _, r in rows], ensure_ascii=False, indent=2))
    else:
        for head, r in rows:
            extra = f", 트윗 {r['tweets']}개 최대 가중치 {max(r['tweet_weights'] or [0])}" if r["platform"] == "x_thread" else ""
            print(f"[{head}] {r['chars']}자, 해시태그 {r['hashtags']}개{extra}")
            for p in r["problems"]:
                print(f"   ERROR {p}")
            for n in r["notes"]:
                print(f"   NOTE  {n}")
    n_err = sum(len(r["problems"]) for _, r in rows)
    print(f"COUNT {'OK' if n_err == 0 else 'OVER'} platforms={len(rows)} errors={n_err}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
