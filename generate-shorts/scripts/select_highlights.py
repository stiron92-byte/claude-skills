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
        # 제목 생성: 첫 문장 또는 앞 30자
        text = w["text"]
        first_sentence = text.split(".")[0].split("?")[0].split("!")[0]
        title = first_sentence[:30].strip()
        if len(first_sentence) > 30:
            title += "..."

        # 후크: 가장 임팩트 있는 문장 (감정 키워드 포함)
        sentences = re.split(r'[.?!]\s*', text) if 'import re' else text.split(". ")
        hook = title

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


# re 모듈 import (score 함수 밖에서 사용)
import re


def main():
    parser = argparse.ArgumentParser(description="규칙 기반 하이라이트 자동 선별")
    parser.add_argument("--transcript", required=True, help="transcript.json 경로")
    parser.add_argument("--output", required=True, help="highlights.json 출력 경로")
    parser.add_argument("--count", type=int, default=10, help="추출할 하이라이트 수 (기본: 10)")
    parser.add_argument("--lang", default="ko", help="언어 (기본: ko)")
    parser.add_argument("--min-duration", type=float, default=15, help="최소 구간 길이 초 (기본: 15)")
    parser.add_argument("--max-duration", type=float, default=60, help="최대 구간 길이 초 (기본: 60)")
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
