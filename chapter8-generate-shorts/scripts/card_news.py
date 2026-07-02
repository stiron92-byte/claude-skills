#!/usr/bin/env python3
"""
카드뉴스 렌더러 — 영상 내용을 요약한 개념 카드(1080x1920 PNG)를 만들고,
옵션으로 카드들을 이어붙인 쇼츠 영상(mp4)까지 조립한다.

디자인 시스템(색/폰트/레이아웃)은 이 스크립트에 고정되어 있고,
"무엇을 쓸지"(카드 내용)만 cards.json으로 받는다 — 내용은 Claude가
영상 대본을 읽고 작성한다 (SKILL.md 카드뉴스 모드 참조).

사용:
  python3 card_news.py --cards output/cards.json --output output/cards/
  python3 card_news.py --cards output/cards.json --output output/cards/ \
      --video output/cards/cards_short.mp4 --seconds 4 --bgm music.mp3
"""

from __future__ import annotations  # py3.9 이하에서 'str | None' 어노테이션 크래시 방지

import argparse
import json
import os
import subprocess
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow가 필요합니다: pip install Pillow --break-system-packages")
    sys.exit(1)


# --- 디자인 시스템 (고정) ---

W, H = 1080, 1920
BG_TOP = (18, 24, 46)      # 딥 네이비
BG_BOT = (8, 9, 16)        # 잉크 블랙
ACCENT = (255, 196, 0)     # 옐로
MINT = (148, 226, 213)     # 민트 (시리즈 라벨)
GRAY = (140, 148, 170)     # 푸터
WHITE = (240, 243, 250)
BOX_BG = (28, 34, 58)      # 포인트 박스
LINE = (60, 68, 96)        # 구분선

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",            # macOS
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",    # macOS
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]

_font_path = None


def get_font(size: int):
    global _font_path
    if _font_path is None:
        for p in FONT_CANDIDATES:
            if os.path.exists(p):
                _font_path = p
                break
        if _font_path is None:
            # fc-list 폴백
            try:
                r = subprocess.run(["fc-list", ":lang=ko", "-f", "%{file}\n"],
                                   capture_output=True, text=True, timeout=5)
                if r.stdout.strip():
                    _font_path = r.stdout.strip().split("\n")[0]
            except Exception:
                pass
    if _font_path:
        try:
            return ImageFont.truetype(_font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# --- 렌더링 헬퍼 ---

def draw_gradient(img):
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOT)))


def fit_font(draw, text: str, size: int, max_width: int, min_size: int = 28):
    """max_width에 들어갈 때까지 폰트 크기를 줄이고, 최소 크기에서도 넘치면
    문자 단위로 잘라 …을 붙인다.
    반환: (font, 사용된 크기, 최종 텍스트, 잘림 여부)
    주의: 내부 개행은 공백으로 정규화한다 — PIL textlength는 멀티라인에서 크래시한다.
    """
    text = " ".join(str(text).split())
    while size > min_size:
        f = get_font(size)
        if draw.textlength(text, font=f) <= max_width:
            return f, size, text, False
        size -= 4
    f = get_font(min_size)
    if draw.textlength(text, font=f) <= max_width:
        return f, min_size, text, False
    while text and draw.textlength(text + "…", font=f) > max_width:
        text = text[:-1]
    return f, min_size, text + "…", True


def wrap_body(draw, text: str, font, max_width: int, max_lines: int = 2):
    """본문을 측정 기반으로 줄바꿈. max_lines 초과분은 …으로 자른다.
    띄어쓰기 없는 긴 문자열(한국어에서 흔함)은 문자 단위로 강제 분할한다 —
    공백 기준으로만 자르면 한 줄이 프레임 밖까지 그려진다."""

    def break_long(word: str):
        chunks, cur = [], ""
        for ch in word:
            if draw.textlength(cur + ch, font=font) <= max_width:
                cur += ch
            else:
                if cur:
                    chunks.append(cur)
                cur = ch
        if cur:
            chunks.append(cur)
        return chunks or [""]

    lines = []
    for raw_line in str(text).split("\n"):
        tokens = []
        for word in raw_line.split():
            if draw.textlength(word, font=font) > max_width:
                tokens.extend(break_long(word))
            else:
                tokens.append(word)
        cur = ""
        for tok in tokens:
            cand = (cur + " " + tok).strip()
            if draw.textlength(cand, font=font) <= max_width:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = tok
        if cur:
            lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def render_card(card: dict, series_label: str, footer: str, out_path: str):
    """카드 1장 렌더링. 반환: 경고 메시지 리스트(넘침으로 잘린 항목 등)."""
    warnings = []
    img = Image.new("RGB", (W, H))
    draw_gradient(img)
    d = ImageDraw.Draw(img)

    # 상단 액센트 바
    d.rectangle([0, 0, W, 14], fill=ACCENT)

    # 시리즈 라벨 + 순번
    try:
        idx = int(card.get("index", 1))
    except (TypeError, ValueError):
        idx = 1
    circled = CIRCLED[idx - 1] if 1 <= idx <= len(CIRCLED) else str(idx)
    label_text = f"{series_label} {circled}" if series_label else circled
    d.text((80, 130), label_text, font=get_font(40), fill=MINT)

    # 타이틀 (최대 2줄) + 펀치라인
    title_lines = [str(t).strip() for t in card.get("title_lines", []) if str(t).strip()]
    if len(title_lines) > 2:
        warnings.append(f"card {idx}: title_lines {len(title_lines)}줄 -> 2줄로 자름")
        title_lines = title_lines[:2]

    y = 260
    for line in title_lines:
        f, used, text, trunc = fit_font(d, line, 120, 920)
        if used < 120 or trunc:
            warnings.append(f"card {idx}: 타이틀 '{text[:12]}' 축소({used}px){' + 잘림' if trunc else ''}")
        d.text((80, y), text, font=f, fill=WHITE, stroke_width=3, stroke_fill=WHITE)
        y += 160

    punch = str(card.get("punch", "")).strip()
    if punch:
        f, used, text, trunc = fit_font(d, punch, 130, 920)
        if used < 130 or trunc:
            warnings.append(f"card {idx}: 펀치라인 축소({used}px){' + 잘림' if trunc else ''}")
        d.text((80, y + 30), text, font=f, fill=ACCENT, stroke_width=4, stroke_fill=ACCENT)
        y += 30 + 175
    else:
        y += 60

    # 구분선
    d.line([(80, y), (1000, y)], fill=LINE, width=3)
    y += 70

    # 포인트 박스 (2~3개)
    points = card.get("points", [])
    if len(points) > 3:
        warnings.append(f"card {idx}: points {len(points)}개 -> 3개로 자름")
        points = points[:3]

    body_font = get_font(46)
    for p in points:
        if not isinstance(p, dict):
            warnings.append(f"card {idx}: points 항목이 객체가 아님 -> 생략")
            continue
        if y + 240 > 1780:
            warnings.append(f"card {idx}: 공간 부족으로 포인트 박스 생략")
            break
        d.rounded_rectangle([80, y, 1000, y + 240], radius=28, fill=BOX_BG)
        d.rounded_rectangle([80, y, 96, y + 240], radius=8, fill=ACCENT)
        f_label, used_l, label_txt, trunc_l = fit_font(d, p.get("label", ""), 44, 820, min_size=30)
        if trunc_l:
            warnings.append(f"card {idx}: 라벨 '{label_txt[:10]}' 잘림")
        d.text((140, y + 38), label_txt, font=f_label, fill=ACCENT)
        body_lines = wrap_body(d, p.get("body", ""), body_font, 820, max_lines=2)
        d.multiline_text((140, y + 108), "\n".join(body_lines),
                         font=body_font, fill=WHITE, spacing=14)
        y += 290

    # 푸터
    if footer:
        d.text((80, 1800), footer, font=get_font(40), fill=GRAY)

    img.save(out_path)
    return warnings


# --- 카드 -> 쇼츠 영상 ---

def build_video(card_paths: list, out_path: str, seconds: float, fade: float,
                fps: int, zoom: bool, bgm: str | None) -> bool:
    """카드 PNG들을 크로스페이드 + 미세 줌으로 이어붙여 1080x1920 mp4 생성."""
    n = len(card_paths)
    if n == 0:
        return False

    inputs = []
    for p in card_paths:
        inputs.extend(["-framerate", str(fps), "-loop", "1", "-t", f"{seconds}", "-i", p])

    frames = int(seconds * fps)
    parts = []
    for i in range(n):
        if zoom:
            # 2배 업스케일 후 줌 — 저해상도 zoompan의 미세 떨림(jitter) 완화
            parts.append(
                f"[{i}:v]scale={W * 2}:{H * 2},"
                f"zoompan=z='1+0.04*on/{frames}':d=1:fps={fps}"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H},"
                f"format=yuv420p[v{i}];"
            )
        else:
            parts.append(f"[{i}:v]format=yuv420p[v{i}];")

    # xfade 체인: 카드당 seconds초, 겹침 fade초
    if n == 1:
        parts.append("[v0]copy[vout]")
    else:
        prev = "v0"
        for i in range(1, n):
            label = "vout" if i == n - 1 else f"x{i}"
            offset = i * (seconds - fade)
            parts.append(
                f"[{prev}][v{i}]xfade=transition=fade:duration={fade}:offset={offset:.3f}[{label}];"
            )
            prev = label
    filter_str = "".join(parts).rstrip(";")

    total = n * seconds - (n - 1) * fade
    cmd = ["ffmpeg", "-y", *inputs]
    if bgm and os.path.exists(bgm):
        # -stream_loop -1: bgm이 영상보다 짧아도 루프. -shortest 대신 -t total로 길이 고정
        # (-shortest는 짧은 bgm에 맞춰 영상 뒷부분을 통째로 잘라버린다)
        cmd.extend(["-stream_loop", "-1", "-i", bgm])
        audio_map = ["-map", f"{n}:a", "-af", "volume=0.6"]
    else:
        cmd.extend(["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=48000:cl=stereo"])
        audio_map = ["-map", f"{n}:a"]

    cmd.extend([
        "-filter_complex", filter_str,
        "-map", "[vout]", *audio_map,
        "-t", f"{total:.2f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print("  영상 조립 타임아웃 (600초 초과)")
        if os.path.exists(out_path):
            os.remove(out_path)
        return False
    if result.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        print(f"  영상 조립 실패:\n{result.stderr[-800:]}")
        if os.path.exists(out_path):
            os.remove(out_path)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="카드뉴스 렌더러 (+ 카드 쇼츠 영상)")
    parser.add_argument("--cards", required=True, help="cards.json 경로 (Claude가 작성)")
    parser.add_argument("--output", required=True, help="PNG 출력 디렉토리")
    parser.add_argument("--video", default="", help="지정 시 카드들을 이어붙인 mp4 생성")
    parser.add_argument("--seconds", type=float, default=4.0, help="카드당 표시 시간(초, 기본 4)")
    parser.add_argument("--fade", type=float, default=0.5, help="크로스페이드 길이(초, 기본 0.5)")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--no-zoom", action="store_true", help="미세 줌 효과 끄기")
    parser.add_argument("--bgm", default="", help="배경음악 파일 (없으면 무음 트랙)")
    args = parser.parse_args()

    if not os.path.exists(args.cards):
        print(f"ERROR: cards.json을 찾을 수 없습니다: {args.cards}")
        sys.exit(1)
    if args.video and args.seconds <= args.fade:
        print(f"ERROR: --seconds({args.seconds})는 --fade({args.fade})보다 커야 합니다 (xfade offset이 음수가 됨)")
        sys.exit(1)
    if args.bgm and not os.path.exists(args.bgm):
        print(f"경고: bgm 파일을 찾을 수 없어 무음으로 진행합니다: {args.bgm}")

    with open(args.cards, "r", encoding="utf-8") as f:
        spec = json.load(f)

    series_label = str(spec.get("series_label", "")).strip()
    footer = str(spec.get("footer", "")).strip()
    cards = spec.get("cards", [])
    if not cards:
        print("ERROR: cards가 비어 있습니다.")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    print(f"=== 카드뉴스 렌더링: {len(cards)}장 ===")
    card_paths = []
    all_warnings = []
    for i, card in enumerate(cards, 1):
        card.setdefault("index", i)
        out_path = os.path.join(args.output, f"card_{i:02d}.png")
        warnings = render_card(card, series_label, footer, out_path)
        all_warnings.extend(warnings)
        card_paths.append(out_path)
        print(f"  [{i:02d}] {out_path}")

    if all_warnings:
        print("\n경고 (레이아웃 자동 조정됨 — 프레임 검수 권장):")
        for w in all_warnings:
            print(f"  - {w}")

    if args.video:
        print(f"\n=== 카드 쇼츠 영상 조립 ===")
        video_dir = os.path.dirname(args.video)
        if video_dir:
            os.makedirs(video_dir, exist_ok=True)
        ok = build_video(card_paths, args.video, args.seconds, args.fade,
                         args.fps, not args.no_zoom, args.bgm or None)
        if ok:
            size_mb = os.path.getsize(args.video) / 1024 / 1024
            print(f"  완료: {args.video} ({size_mb:.1f}MB)")
        else:
            sys.exit(1)

    print("\n완료. 각 PNG를 열어 텍스트 넘침/겹침이 없는지 확인하세요.")


if __name__ == "__main__":
    main()
