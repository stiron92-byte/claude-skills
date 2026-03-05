#!/usr/bin/env python3
"""텍스트 무드 분석 기반 자동 BGM 생성

Gemini API로 텍스트의 분위기를 분석하고,
FFmpeg 오디오 합성 기능으로 분위기에 맞는 앰비언트 BGM을 생성합니다.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

from dotenv import load_dotenv

load_dotenv()


# 무드별 음악 파라미터 프리셋
MOOD_PRESETS = {
    "calm": {
        "name": "차분한",
        "base_freq": 220,       # A3
        "chord": [1, 1.25, 1.5],  # minor triad ratios
        "tempo_bpm": 60,
        "pad_freqs": [110, 165, 220, 330],
        "lfo_rate": 0.05,       # 매우 느린 변조
        "reverb_delay": 0.8,
        "brightness": 0.3,
    },
    "inspirational": {
        "name": "영감/동기부여",
        "base_freq": 261.63,    # C4
        "chord": [1, 1.25, 1.5, 2],  # C minor + octave
        "tempo_bpm": 80,
        "pad_freqs": [130.81, 164.81, 196, 261.63, 329.63],
        "lfo_rate": 0.08,
        "reverb_delay": 0.6,
        "brightness": 0.5,
    },
    "warm": {
        "name": "따뜻한",
        "base_freq": 196,       # G3
        "chord": [1, 1.25, 1.5, 1.875],
        "tempo_bpm": 72,
        "pad_freqs": [98, 146.83, 196, 246.94],
        "lfo_rate": 0.06,
        "reverb_delay": 0.7,
        "brightness": 0.4,
    },
    "dramatic": {
        "name": "극적인",
        "base_freq": 146.83,    # D3
        "chord": [1, 1.189, 1.498],  # minor
        "tempo_bpm": 90,
        "pad_freqs": [73.42, 146.83, 174.61, 220, 293.66],
        "lfo_rate": 0.1,
        "reverb_delay": 0.5,
        "brightness": 0.6,
    },
    "hopeful": {
        "name": "희망적인",
        "base_freq": 293.66,    # D4
        "chord": [1, 1.26, 1.498, 2],  # major
        "tempo_bpm": 76,
        "pad_freqs": [146.83, 220, 293.66, 369.99],
        "lfo_rate": 0.07,
        "reverb_delay": 0.65,
        "brightness": 0.55,
    },
    "meditative": {
        "name": "명상적인",
        "base_freq": 174.61,    # F3
        "chord": [1, 1.335, 1.498],  # sus4
        "tempo_bpm": 50,
        "pad_freqs": [87.31, 130.81, 174.61, 261.63],
        "lfo_rate": 0.03,
        "reverb_delay": 1.0,
        "brightness": 0.2,
    },
}


def get_client():
    """Gemini API 클라이언트 생성"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def analyze_mood_keywords(text):
    """키워드 기반 무드 감지 (오프라인 폴백)"""
    mood_keywords = {
        "calm": ["평화", "고요", "안정", "차분", "쉬", "편안", "느긋", "잔잔"],
        "meditative": ["명상", "수면", "호흡", "마음", "내면", "고요", "침묵", "영혼"],
        "inspirational": ["성공", "도전", "용기", "꿈", "희망", "성장", "노력", "열정", "시작", "해내", "할 수"],
        "hopeful": ["희망", "밝", "미래", "긍정", "기대", "빛", "새로운", "가능"],
        "warm": ["감사", "사랑", "따뜻", "행복", "가족", "친구", "함께", "나누", "소중"],
        "dramatic": ["전쟁", "역사", "위기", "운명", "비극", "극적", "전환", "혁명", "투쟁"],
    }

    scores = {mood: 0 for mood in mood_keywords}
    for mood, keywords in mood_keywords.items():
        for kw in keywords:
            scores[mood] += text.count(kw)

    best_mood = max(scores, key=scores.get)
    if scores[best_mood] == 0:
        best_mood = "inspirational"

    return best_mood


def analyze_mood(client, text, model="gemini-2.5-flash"):
    """Gemini로 텍스트 무드 분석"""
    available_moods = ", ".join(MOOD_PRESETS.keys())

    prompt = f"""Analyze the overall mood/atmosphere of the following text and select the SINGLE most fitting mood category.

Available moods: {available_moods}

Text:
{text[:2000]}

Respond with ONLY the mood name (one word from the available list), nothing else."""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        mood = response.text.strip().lower().replace('"', '').replace("'", "")

        if mood in MOOD_PRESETS:
            return mood
        # 부분 매칭 시도
        for key in MOOD_PRESETS:
            if key in mood or mood in key:
                return key
        print(f"  [WARN] 인식할 수 없는 무드 '{mood}', 기본값 'inspirational' 사용")
        return "inspirational"
    except Exception as e:
        print(f"  [WARN] 무드 분석 실패: {e}, 기본값 'inspirational' 사용")
        return "inspirational"


def generate_ambient_bgm(mood, duration, output_path, sample_rate=44100):
    """FFmpeg로 앰비언트 BGM 생성

    여러 사인파를 레이어링하고 LFO 변조 + 리버브로 앰비언트 사운드 생성
    """
    preset = MOOD_PRESETS[mood]
    pad_freqs = preset["pad_freqs"]
    lfo_rate = preset["lfo_rate"]
    brightness = preset["brightness"]

    # 각 패드 레이어의 aevalsrc 표현식 생성
    # 느린 LFO로 볼륨 변조하여 자연스러운 패드 사운드 구현
    layers = []
    for i, freq in enumerate(pad_freqs):
        # 각 레이어에 서로 다른 LFO 위상과 속도 적용
        phase = i * 0.7
        rate = lfo_rate * (1 + i * 0.15)
        # 고주파일수록 볼륨 낮게 (brightness로 제어)
        vol = max(0.08, 0.3 - (i * 0.05 * (1 - brightness)))
        # aevalsrc: 사인파 * LFO 엔벨로프
        expr = f"{vol}*sin(2*PI*{freq}*t)*((1+sin(2*PI*{rate}*t+{phase}))/2)"
        layers.append(expr)

    # 서브 베이스 (매우 낮은 주파수 드론)
    sub_freq = preset["base_freq"] / 2
    layers.append(f"0.15*sin(2*PI*{sub_freq}*t)*((1+sin(2*PI*{lfo_rate*0.5}*t))/2)")

    # 모든 레이어 합산
    combined_expr = "+".join(layers)
    # 클리핑 방지를 위해 전체 볼륨 조정
    total_layers = len(layers)
    master_vol = min(0.7, 1.5 / total_layers)
    final_expr = f"({combined_expr})*{master_vol}"

    # fade-in (3초), fade-out (3초) 적용
    fade_in = 3.0
    fade_out = 3.0
    fade_out_start = max(0, duration - fade_out)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        raw_path = tmp.name

    # Step 1: 원시 앰비언트 사운드 생성
    cmd1 = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"aevalsrc={final_expr}:s={sample_rate}:d={duration}",
        "-t", str(duration),
        raw_path,
    ]

    result = subprocess.run(cmd1, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  [ERROR] 앰비언트 생성 실패: {result.stderr[:300]}")
        try:
            os.unlink(raw_path)
        except OSError:
            pass
        return False

    # Step 2: 리버브(에코) + 로우패스 필터 + 페이드 적용
    reverb_delay = int(preset["reverb_delay"] * 1000)
    # lowpass로 거친 고주파 제거, aecho로 공간감 추가
    filter_chain = (
        f"lowpass=f={2000 + int(brightness * 4000)},"
        f"aecho=0.8:0.7:{reverb_delay}:0.4,"
        f"afade=t=in:st=0:d={fade_in},"
        f"afade=t=out:st={fade_out_start}:d={fade_out},"
        f"loudnorm=I=-24:TP=-3:LRA=7"
    )

    cmd2 = [
        "ffmpeg", "-y",
        "-i", raw_path,
        "-af", filter_chain,
        "-c:a", "aac",
        "-b:a", "128k",
        output_path,
    ]

    result = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)

    try:
        os.unlink(raw_path)
    except OSError:
        pass

    if result.returncode != 0:
        print(f"  [ERROR] BGM 후처리 실패: {result.stderr[:300]}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="텍스트 무드 기반 자동 BGM 생성")
    parser.add_argument("--segments", required=True, help="segments.json 경로")
    parser.add_argument("--config", required=True, help="config.yaml 경로")
    parser.add_argument("--output", required=True, help="출력 BGM 파일 경로 (.m4a)")
    parser.add_argument("--duration", type=float, default=0,
                        help="BGM 길이 (초). 0이면 세그먼트 총 길이 + 여유분으로 자동 계산")
    parser.add_argument("--mood", default=None,
                        help="무드 직접 지정 (calm/inspirational/warm/dramatic/hopeful/meditative)")
    parser.add_argument("--offline", action="store_true",
                        help="오프라인 모드 (키워드 기반 무드 감지)")
    args = parser.parse_args()

    import yaml
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(args.segments, "r", encoding="utf-8") as f:
        segments = json.load(f)

    audio_model = config.get("AUDIO_MODEL", "gemini-2.5-flash")

    # 전체 텍스트 추출
    full_text = "\n".join(seg.get("text", "") for seg in segments)

    # BGM 길이 계산
    if args.duration > 0:
        duration = args.duration
    else:
        total_audio = sum(seg.get("duration", 10) for seg in segments)
        segment_gap = config.get("SEGMENT_GAP", 0.5)
        duration = total_audio + (len(segments) * segment_gap) + 5  # 여유분 5초

    print(f"[Phase 4.5] BGM 자동 생성 시작")
    print(f"  BGM 길이: {duration:.1f}초")

    # 무드 분석
    if args.mood and args.mood in MOOD_PRESETS:
        mood = args.mood
        print(f"  무드 (직접 지정): {mood} ({MOOD_PRESETS[mood]['name']})")
    elif args.offline:
        print(f"  키워드 기반 무드 분석 중 (오프라인)...")
        mood = analyze_mood_keywords(full_text)
        print(f"  감지된 무드: {mood} ({MOOD_PRESETS[mood]['name']})")
    else:
        print(f"  텍스트 무드 분석 중...")
        client = get_client()
        mood = analyze_mood(client, full_text, model=audio_model)
        print(f"  감지된 무드: {mood} ({MOOD_PRESETS[mood]['name']})")

    # BGM 생성
    print(f"  앰비언트 BGM 합성 중...")
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    if generate_ambient_bgm(mood, duration, args.output):
        file_size = os.path.getsize(args.output)
        print(f"  BGM 생성 완료: {args.output}")
        print(f"  크기: {file_size / 1024:.1f}KB")
        print(f"\n[Phase 4.5] BGM 생성 완료")
    else:
        print(f"\n[Phase 4.5] BGM 생성 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
