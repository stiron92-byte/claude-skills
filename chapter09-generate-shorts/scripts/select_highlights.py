#!/usr/bin/env python3
"""
규칙 기반 하이라이트 자동 선별
- transcript.json을 입력으로 받아 쇼츠 후보 구간을 추출
- 감정 키워드, 정보 밀도, 독립성 기준으로 스코어링
- 슬라이딩 윈도우로 15~60초 구간 생성
"""

import argparse
import json
import math
import os
import re
import sys


# --- 감정/강조 키워드 사전 ---

EMOTION_KEYWORDS_KO = {
    # 놀람/충격 (가중치 높음)
    "놀라": 5, "충격": 5, "대박": 5, "헐": 4, "미쳤": 4, "세상에": 4,
    "말도 안": 4, "어머": 3, "우와": 3, "진짜로": 3,
    # 강조/중요
    "진짜": 3, "정말": 3, "심각": 4, "중요": 4, "핵심": 5,
    "비밀": 4, "절대": 4, "반드시": 3, "꼭": 3, "무조건": 3,
    # 정보/팁
    "팁": 4, "비법": 4, "방법": 3, "노하우": 4, "꿀팁": 5,
    "알려드": 3, "공개": 3, "추천": 3,
    # 유머/반응
    "웃기": 3, "ㅋㅋ": 2, "하하": 2, "재밌": 3,
    # 전환/임팩트
    "근데": 2, "그런데": 2, "사실은": 4, "알고 보니": 4,
    "반전": 5, "실화": 4,
}

EMOTION_KEYWORDS_EN = {
    "amazing": 5, "incredible": 5, "shocking": 5, "unbelievable": 5,
    "important": 4, "secret": 4, "tip": 4, "must": 3, "key": 3,
    "actually": 3, "truth": 4, "never": 3, "always": 3,
    "wow": 3, "crazy": 4, "insane": 4, "game changer": 5,
}

# 맥락 의존 표현 (독립성 감점)
CONTEXT_WORDS_KO = [
    "이것", "그것", "저것", "이건", "그건",
    "아까", "방금", "위에서", "앞에서", "말씀드린",
    "그래서", "그러니까", "그렇기 때문에",
    "다시 말하면", "즉",
]

CONTEXT_WORDS_EN = [
    "this one", "that one", "as I said", "earlier",
    "as mentioned", "going back to", "like I said",
]


def _dedupe_repeats(text: str) -> str:
    """연속으로 반복되는 어구를 하나로 줄인다.
    YouTube 자동자막은 롤링 방식이라 같은 구절이 2~3번 겹쳐 들어온다
    (예: "쭉 가져오고 준비를 한 다음에 쭉 가져오고 준비를 한 다음에 쭉 가져오고 준비를 한 다음에").
    2회뿐 아니라 3회 이상 연속 반복도 한 번으로 줄인다.
    """
    words = text.split()
    out = []
    i = 0
    n = len(words)
    while i < n:
        matched = False
        # 길이가 긴 반복부터 검사(최대 8단어)
        for length in range(min(8, (n - i) // 2), 0, -1):
            block = words[i:i + length]
            # 같은 블록이 몇 번 연속되는지 센다
            j = i + length
            while j + length <= n and words[j:j + length] == block:
                j += length
            if j > i + length:  # 최소 1회 반복 발견 -> 블록 하나만 남기고 전부 스킵
                out.extend(block)
                i = j
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return " ".join(out)


def clean_caption_text(text: str) -> str:
    """자막 원문을 제목/후크로 쓸 수 있게 정리한다.
    자동자막에는 화자 표시(>>), 효과음 태그([음악],[박수]), 롤링 중복이 섞여 있어
    이를 제거하지 않으면 인트로 카드와 해시태그에 그대로 노출된다.
    """
    if not text:
        return ""
    t = text
    # 효과음/설명 태그 제거: [음악], (웃음), （박수） 등
    t = re.sub(r"[\[\(（][^\]\)）]*[\]\)）]", " ", t)
    t = t.replace("♪", " ")
    # 화자/이어짐 표시 제거: >>, ->>, >>>
    t = re.sub(r"-?>>+", " ", t)
    # 공백 정리 후 반복 어구 축약
    t = re.sub(r"\s+", " ", t).strip()
    t = _dedupe_repeats(t)
    return re.sub(r"\s+", " ", t).strip()


def make_title(text: str, index: int, max_len: int = 28) -> tuple:
    """정리된 자막에서 (제목, 후크)를 만든다."""
    clean = clean_caption_text(text)
    if not clean:
        return (f"하이라이트 {index}", f"하이라이트 {index}")
    # 첫 문장(마침표/물음표/느낌표 기준) 우선, 없으면 앞부분
    first = re.split(r"[.?!]\s", clean)[0].strip()
    base = first if first else clean
    title = base[:max_len].strip()
    if len(base) > max_len:
        title += "…"
    hook = clean[:60].strip()
    return (title or f"하이라이트 {index}", hook or title)


def score_segment(text: str, duration: float, lang: str = "ko") -> dict:
    """세그먼트 스코어링 (감정, 정보밀도, 독립성)"""
    scores = {"emotion": 0, "density": 0, "independence": 0, "total": 0}

    text_lower = text.lower()
    words = text.split()
    word_count = len(words)

    # 1. 감정 강도
    keywords = EMOTION_KEYWORDS_KO if lang == "ko" else EMOTION_KEYWORDS_EN
    for keyword, weight in keywords.items():
        count = text_lower.count(keyword)
        scores["emotion"] += count * weight
    scores["emotion"] = min(scores["emotion"], 40)  # 상한

    # 2. 정보 밀도 (단어 수 / 시간)
    if duration > 0:
        density = word_count / duration
        if lang == "ko":
            # 한국어: 초당 2~4음절이 적당
            chars = len(text.replace(" ", ""))
            char_density = chars / duration
            scores["density"] = min(char_density * 3, 30)
        else:
            scores["density"] = min(density * 8, 30)

    # 3. 독립성 (맥락 의존 표현 감점)
    context_words = CONTEXT_WORDS_KO if lang == "ko" else CONTEXT_WORDS_EN
    context_penalty = 0
    for cw in context_words:
        if cw in text_lower:
            context_penalty += 3
    scores["independence"] = max(20 - context_penalty, 0)

    # 4. 길이 보너스 (너무 짧거나 긴 것은 감점)
    length_bonus = 0
    if 20 <= duration <= 45:
        length_bonus = 10  # 최적 길이
    elif 15 <= duration <= 60:
        length_bonus = 5
    else:
        length_bonus = -5

    scores["total"] = (
        scores["emotion"] + scores["density"] +
        scores["independence"] + length_bonus
    )
    return scores


def build_windows(chunks: list, min_sec: float = 15, max_sec: float = 60) -> list:
    """자막 청크로부터 슬라이딩 윈도우 구간 생성"""
    if not chunks:
        return []

    windows = []
    n = len(chunks)

    for i in range(n):
        start_time = chunks[i]["timestamp"][0]
        texts = []

        for j in range(i, n):
            end_time = chunks[j]["timestamp"][1]
            duration = end_time - start_time

            if duration > max_sec:
                break

            texts.append(chunks[j]["text"])

            if duration >= min_sec:
                windows.append({
                    "start": round(start_time, 2),
                    "end": round(end_time, 2),
                    "duration": round(duration, 2),
                    "text": " ".join(texts),
                    "chunk_start": i,
                    "chunk_end": j,
                })

    return windows


def select_top_highlights(
    windows: list, count: int = 10, lang: str = "ko", min_gap: float = 10
) -> list:
    """윈도우를 스코어링하고 겹치지 않는 상위 N개 선별"""
    # 스코어링
    for w in windows:
        w["scores"] = score_segment(w["text"], w["duration"], lang)
        w["score"] = w["scores"]["total"]

    # 스코어 내림차순 정렬
    windows.sort(key=lambda x: x["score"], reverse=True)

    # 겹침 제거 (greedy)
    selected = []
    for w in windows:
        if len(selected) >= count:
            break

        overlaps = False
        for s in selected:
            # 구간이 겹치는지 체크 (min_gap 간격 유지)
            if not (w["end"] + min_gap <= s["start"] or w["start"] >= s["end"] + min_gap):
                overlaps = True
                break

        if not overlaps:
            selected.append(w)

    # 시간 순 정렬
    selected.sort(key=lambda x: x["start"])

    # 최종 형식으로 변환
    highlights = []
    for idx, w in enumerate(selected, 1):
        text = w["text"]
        # 자막 원문을 정리해 제목/후크 생성 (>>, 효과음 태그, 롤링 중복 제거)
        title, hook = make_title(text, idx)

        highlights.append({
            "index": idx,
            "start": w["start"],
            "end": w["end"],
            "title": title,
            "reason": (
                f"감정={w['scores']['emotion']}, "
                f"밀도={w['scores']['density']:.0f}, "
                f"독립성={w['scores']['independence']}, "
                f"총점={w['score']:.0f}"
            ),
            "hook": hook,
            "transcript": text,
        })

    return highlights


def select_candidates(windows: list, count: int = 25, lang: str = "ko") -> list:
    """Claude 큐레이션용 후보 목록을 만든다.

    최종 선별이 아니라 '검토 대상'이므로 자동 모드보다 겹침을 느슨하게 허용해
    선택지를 넓힌다. 점수는 참고용일 뿐 — 규칙 스코어는 감정 키워드 개수를 셀 뿐
    내용의 완결성/후크를 이해하지 못하므로, 최종 판단은 Claude가 내용을 읽고 한다.
    """
    for w in windows:
        w["scores"] = score_segment(w["text"], w["duration"], lang)
        w["score"] = w["scores"]["total"]

    windows.sort(key=lambda x: x["score"], reverse=True)

    selected = []
    for w in windows:
        if len(selected) >= count:
            break
        # 이미 뽑힌 후보와 70% 이상 겹치면 스킵 (다양성 확보)
        dup = False
        for s in selected:
            inter = min(w["end"], s["end"]) - max(w["start"], s["start"])
            if inter > 0 and inter >= 0.7 * min(w["duration"], s["duration"]):
                dup = True
                break
        if not dup:
            selected.append(w)

    selected.sort(key=lambda x: x["start"])
    return [
        {
            "start": w["start"],
            "end": w["end"],
            "duration": w["duration"],
            "score": round(w["score"], 1),
            "text": clean_caption_text(w["text"]),
        }
        for w in selected
    ]


def main():
    parser = argparse.ArgumentParser(description="규칙 기반 하이라이트 자동 선별")
    parser.add_argument("--transcript", required=True, help="transcript.json 경로")
    parser.add_argument("--output", required=True, help="highlights.json 출력 경로")
    parser.add_argument("--count", type=int, default=10, help="추출할 하이라이트 수 (기본: 10)")
    parser.add_argument("--lang", default="ko", help="언어 (기본: ko)")
    parser.add_argument("--min-duration", type=float, default=15, help="최소 구간 길이 초 (기본: 15)")
    parser.add_argument("--max-duration", type=float, default=60, help="최대 구간 길이 초 (기본: 60)")
    parser.add_argument(
        "--mode", choices=["auto", "candidates"], default="auto",
        help="auto: 최종 highlights.json 자동 생성(품질 낮음) | candidates: Claude 큐레이션용 후보 목록 생성(권장)"
    )
    parser.add_argument("--candidates-count", type=int, default=25, help="candidates 모드 후보 수 (기본: 25)")
    args = parser.parse_args()

    if not os.path.exists(args.transcript):
        print(f"ERROR: 파일을 찾을 수 없습니다: {args.transcript}")
        sys.exit(1)

    with open(args.transcript, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    chunks = transcript.get("chunks", [])
    if not chunks:
        print("ERROR: 자막 데이터가 비어있습니다.")
        sys.exit(1)

    total_duration = chunks[-1]["timestamp"][1] if chunks else 0
    print(f"=== 하이라이트 자동 선별 ===")
    print(f"자막 세그먼트: {len(chunks)}개")
    print(f"영상 길이: {total_duration:.0f}초 ({total_duration / 60:.1f}분)")
    print(f"구간 범위: {args.min_duration}~{args.max_duration}초")
    print(f"목표: {args.count}개")
    print()

    # 윈도우 생성
    print("슬라이딩 윈도우 생성 중...")
    windows = build_windows(chunks, args.min_duration, args.max_duration)
    print(f"  후보 윈도우: {len(windows)}개")

    if not windows:
        print("ERROR: 조건에 맞는 구간이 없습니다. --min-duration 값을 줄여보세요.")
        sys.exit(1)

    # candidates 모드: Claude가 검토할 후보 목록만 만들고 종료
    if args.mode == "candidates":
        print("후보 스코어링 중 (Claude 큐레이션용)...")
        candidates = select_candidates(windows, args.candidates_count, args.lang)
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        payload = {
            "video_duration": round(total_duration, 1),
            "note": (
                "이 파일은 후보 목록이다. Claude가 내용을 읽고 최종 highlights.json을 "
                "작성한다 (SKILL.md Phase 2b 참조). score는 참고용 규칙 점수일 뿐이다."
            ),
            "candidates": candidates,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n=== 후보 {len(candidates)}개 저장: {args.output} ===")
        for c in candidates[:10]:
            print(f"  {c['start']:.0f}s-{c['end']:.0f}s ({c['duration']:.0f}s, {c['score']:.0f}점) | {c['text'][:40]}")
        if len(candidates) > 10:
            print(f"  ... 외 {len(candidates) - 10}개")
        return

    # 스코어링 + 선별
    print("스코어링 및 선별 중...")
    highlights = select_top_highlights(windows, args.count, args.lang)

    if not highlights:
        print("ERROR: 하이라이트를 선별할 수 없습니다.")
        sys.exit(1)

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(highlights, f, ensure_ascii=False, indent=2)

    print(f"\n=== 선별 완료: {len(highlights)}개 ===")
    for h in highlights:
        print(f"  [{h['index']:02d}] {h['start']:.0f}s-{h['end']:.0f}s ({h['end']-h['start']:.0f}s) | {h['title']}")
        print(f"       {h['reason']}")
    print(f"\n출력: {args.output}")


if __name__ == "__main__":
    main()
