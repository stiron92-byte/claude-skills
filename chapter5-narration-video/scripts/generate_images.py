#!/usr/bin/env python3
"""Gemini API를 사용한 세그먼트별 이미지 생성

고도화 포인트:
1. Gemini 텍스트 모델로 나레이션 텍스트 → 구체적 시각 프롬프트 변환
2. 전체 맥락(제목, 스타일, 이전 세그먼트)을 고려한 일관된 이미지 생성
3. 추상적 명언도 구체적 장면/오브제로 시각화
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# PIL 폴백용 그라디언트 색상 팔레트
GRADIENT_PALETTES = [
    ((25, 25, 70), (70, 40, 110)),       # deep purple
    ((15, 50, 80), (35, 90, 130)),       # ocean blue
    ((55, 35, 25), (110, 70, 40)),       # warm brown
    ((15, 45, 45), (35, 90, 80)),        # forest teal
    ((65, 25, 45), (120, 45, 70)),       # burgundy rose
    ((25, 25, 45), (60, 60, 90)),        # twilight gray
    ((70, 45, 15), (130, 80, 30)),       # golden amber
    ((15, 35, 55), (45, 70, 110)),       # steel blue
    ((45, 25, 55), (90, 50, 100)),       # violet
    ((35, 45, 25), (70, 90, 50)),        # olive green
]


def get_client():
    """Gemini API 클라이언트 생성"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def find_korean_font():
    """시스템에서 한글 폰트 경로 탐색"""
    font_candidates = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        "/Library/Fonts/NotoSansCJKkr-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for font in font_candidates:
        if os.path.exists(font):
            return font
    return None


def generate_image_pil(text, index, total, output_path):
    """PIL로 그라디언트 배경 + 텍스트 카드 이미지 생성 (오프라인 폴백)"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", "Pillow"],
            capture_output=True, timeout=120,
        )
        from PIL import Image, ImageDraw, ImageFont

    width, height = 1920, 1080

    # 세그먼트별 다른 그라디언트
    palette_idx = (index - 1) % len(GRADIENT_PALETTES)
    color_top, color_bottom = GRADIENT_PALETTES[palette_idx]

    # 그라디언트 배경
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 중앙에 반투명 패널
    panel_margin = 120
    panel_color = (0, 0, 0)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [panel_margin, panel_margin * 2, width - panel_margin, height - panel_margin * 2],
        radius=30, fill=(0, 0, 0, 100),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 폰트
    font_path = find_korean_font()
    font_size = 44
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # 텍스트 줄바꿈 (한 줄 최대 22자)
    max_chars = 22
    lines = []
    for i in range(0, len(text), max_chars):
        lines.append(text[i:i + max_chars])

    line_height = font_size + 24
    total_text_height = len(lines) * line_height
    y_start = (height - total_text_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = y_start + i * line_height
        # 그림자
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        # 본체
        draw.text((x, y), line, font=font, fill=(255, 255, 255))

    # 세그먼트 번호
    try:
        small_font = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default()
    except Exception:
        small_font = ImageFont.load_default()
    draw.text((width - 90, height - 45), f"{index}/{total}", font=small_font, fill=(180, 180, 180))

    img.save(output_path, "PNG")
    return True


def build_visual_prompts(client, segments, style, language="ko"):
    """Gemini 텍스트 모델로 모든 세그먼트의 시각 프롬프트를 일괄 생성

    핵심: 추상적 텍스트를 구체적인 장면/오브제/구도로 변환
    """
    texts_block = ""
    for seg in segments:
        texts_block += f"[{seg['index']}] {seg['text']}\n"

    prompt = f"""You are an expert visual prompt engineer for AI image generation.

Task: Convert each narration text below into a specific, visual image prompt.

Rules:
1. Each prompt must describe a CONCRETE scene, object, or visual metaphor — never abstract concepts
2. Include: subject, composition, lighting, color mood, camera angle
3. All prompts must share a consistent visual world (same art style, color palette, recurring motifs)
4. For abstract/philosophical texts: find a tangible metaphor
   - "용기" → a person standing at the edge of a cliff at dawn, warm golden light
   - "시간의 소중함" → an hourglass with golden sand, soft morning light through a window
   - "함께 가면 멀리 간다" → a group of silhouettes walking together on a long road toward sunset
5. NO text/typography/letters in the image
6. Each prompt should be 2-3 sentences in English
7. Art style to maintain: {style}

Narration texts:
{texts_block}

Output format (one per line, keep the index):
[1] <image prompt>
[2] <image prompt>
...
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        result_text = response.text

        # 결과 파싱
        import re
        prompts = {}
        for match in re.finditer(r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|\Z)', result_text, re.DOTALL):
            idx = int(match.group(1))
            prompt_text = match.group(2).strip()
            prompts[idx] = prompt_text

        return prompts

    except Exception as e:
        print(f"  [WARN] 시각 프롬프트 일괄 생성 실패: {e}")
        return {}


def build_single_visual_prompt(client, text, style, prev_prompt=""):
    """단일 세그먼트의 시각 프롬프트 생성 (폴백용)"""
    prompt = f"""Convert this narration text into a concrete visual image prompt for AI image generation.

Text: "{text}"

Rules:
- Describe a SPECIFIC scene with tangible objects, not abstract concepts
- Include: subject, composition, lighting, color mood
- Art style: {style}
- NO text/letters in the image
- 2-3 sentences in English
{"- Maintain visual consistency with previous image: " + prev_prompt[:100] if prev_prompt else ""}

Output only the image prompt, nothing else."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"  [WARN] 단일 프롬프트 생성 실패: {e}")
        return None


def extract_visual_keywords(text):
    """텍스트에서 시각적 키워드를 추출하여 기본 프롬프트 구성 (최종 폴백)"""
    # 한국어 키워드 → 시각적 장면 매핑
    keyword_scenes = {
        "성공": "a golden sunrise over mountain peaks, triumphant warm light",
        "실패": "a single seedling growing through cracked dry earth, resilience",
        "용기": "a person standing confidently at the edge of a cliff at dawn",
        "시간": "an elegant hourglass with golden sand, soft window light",
        "배움": "an open book with light emanating from its pages in a cozy library",
        "감사": "hands gently holding a glowing warm light, gratitude",
        "두려움": "a path leading from dark forest shadows into bright sunlight",
        "꿈": "a silhouette reaching toward stars in a twilight sky",
        "변화": "a butterfly emerging from a cocoon, transformation, morning dew",
        "함께": "silhouettes of people walking together on a road toward golden sunset",
        "고통": "rain drops on a window with warm light glowing behind, hope after pain",
        "시작": "a single footstep on fresh snow, new beginning, crisp morning light",
        "길": "a winding path through a peaceful landscape, journey",
        "마음": "a warm glowing lantern in gentle hands, inner peace",
        "힘": "a strong oak tree with deep roots and wide branches, golden hour",
        "행복": "warm sunlight streaming through autumn leaves, peaceful scene",
        "사랑": "two intertwined trees growing together, soft warm light",
        "희망": "a lighthouse beam cutting through fog at dawn, guiding light",
        "인생": "a long winding river flowing through varied landscapes, life journey",
        "노력": "hands carefully tending a garden, dedication, soft morning light",
    }

    for keyword, scene in keyword_scenes.items():
        if keyword in text:
            return scene

    # 매칭 없으면 범용 장면
    return "a serene landscape with soft natural light, contemplative mood, peaceful atmosphere"


def generate_image(client, prompt, style, model, output_path, retries=3):
    """단일 이미지 생성"""
    from google.genai import types

    full_prompt = f"{prompt}. Art style: {style}. No text, no letters, no words in the image."

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    img_data = part.inline_data.data
                    if isinstance(img_data, str):
                        img_data = base64.b64decode(img_data)
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    return True

            print(f"  [WARN] 이미지 데이터 없음 (시도 {attempt + 1}/{retries})")

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait = 2 ** (attempt + 1) * 5
                print(f"  [RATE_LIMIT] {wait}초 대기 후 재시도 ({attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                print(f"  [ERROR] 이미지 생성 실패: {e} (시도 {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(3)

    return False


def main():
    parser = argparse.ArgumentParser(description="세그먼트별 이미지 생성")
    parser.add_argument("--segments", required=True, help="segments.json 경로")
    parser.add_argument("--config", required=True, help="config.yaml 경로")
    parser.add_argument("--output", required=True, help="출력 디렉토리")
    parser.add_argument("--style", default=None, help="IMAGE_STYLE 오버라이드 (프리셋 또는 커스텀)")
    parser.add_argument("--offline", action="store_true", help="오프라인 모드 (PIL 텍스트 카드)")
    args = parser.parse_args()

    import yaml
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(args.segments, "r", encoding="utf-8") as f:
        segments = json.load(f)

    os.makedirs(args.output, exist_ok=True)
    total = len(segments)
    success_count = 0
    fail_count = 0

    # --- 오프라인 모드: PIL 텍스트 카드 ---
    if args.offline:
        print(f"[Phase 2] PIL 텍스트 카드 생성 시작 ({total}개 세그먼트)")
        for i, seg in enumerate(segments):
            idx = i + 1
            output_path = os.path.join(args.output, f"img_{idx:03d}.png")

            if os.path.exists(output_path):
                print(f"  [{idx}/{total}] 이미 존재: {output_path}")
                seg["image_path"] = output_path
                success_count += 1
                continue

            text = seg.get("text", "")
            print(f"  [{idx}/{total}] 텍스트 카드 생성 중...")

            if generate_image_pil(text, idx, total, output_path):
                seg["image_path"] = output_path
                success_count += 1
                print(f"  [{idx}/{total}] 완료")
            else:
                fail_count += 1
                print(f"  [{idx}/{total}] 실패")

        with open(args.segments, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        print(f"\n[Phase 2] PIL 이미지 생성 완료: 성공 {success_count}, 실패 {fail_count}")
        if fail_count > 0:
            sys.exit(1)
        return

    # --- 온라인 모드: Gemini API ---
    style = args.style or config.get("IMAGE_STYLE", "minimal illustration, soft pastel colors, clean white background")
    model = config.get("IMAGE_MODEL", "gemini-2.5-flash-image")
    delay = config.get("IMAGE_DELAY", 3)
    language = config.get("LANGUAGE", "ko")

    client = get_client()

    # --- Phase 2a: 시각 프롬프트 일괄 생성 ---
    print(f"[Phase 2a] 시각 프롬프트 생성 중 ({total}개 세그먼트)...")
    visual_prompts = build_visual_prompts(client, segments, style, language)

    if visual_prompts:
        print(f"  Gemini로 {len(visual_prompts)}개 시각 프롬프트 생성 완료")
        for idx, vp in visual_prompts.items():
            print(f"    [{idx}] {vp[:80]}...")
    else:
        print("  [WARN] 일괄 프롬프트 생성 실패, 개별 생성으로 전환")

    time.sleep(2)

    # --- Phase 2b: 이미지 생성 ---
    print(f"\n[Phase 2b] 이미지 생성 시작 ({total}개 세그먼트)")

    prev_prompt = ""
    for i, seg in enumerate(segments):
        idx = i + 1
        output_path = os.path.join(args.output, f"img_{idx:03d}.png")

        if os.path.exists(output_path):
            print(f"  [{idx}/{total}] 이미 존재: {output_path}")
            seg["image_path"] = output_path
            success_count += 1
            continue

        text = seg.get("text", "")

        if idx in visual_prompts:
            prompt = visual_prompts[idx]
        else:
            prompt = build_single_visual_prompt(client, text, style, prev_prompt)
            if not prompt:
                prompt = extract_visual_keywords(text)
                print(f"  [{idx}/{total}] 키워드 폴백 프롬프트 사용")

        seg["image_prompt"] = prompt
        prev_prompt = prompt

        print(f"  [{idx}/{total}] 이미지 생성 중...")
        print(f"    프롬프트: {prompt[:100]}...")

        if generate_image(client, prompt, style, model, output_path):
            seg["image_path"] = output_path
            success_count += 1
            print(f"  [{idx}/{total}] 완료: {output_path}")
        else:
            fail_count += 1
            print(f"  [{idx}/{total}] 실패")

        if i < total - 1:
            time.sleep(delay)

    # segments.json 업데이트
    with open(args.segments, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"\n[Phase 2] 이미지 생성 완료: 성공 {success_count}, 실패 {fail_count}")

    if fail_count > 0:
        print(f"[WARN] {fail_count}개 세그먼트의 이미지 생성에 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
