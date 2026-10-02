#!/usr/bin/env python3
"""Gemini TTS API를 사용한 세그먼트별 나레이션 생성"""

import argparse
import asyncio
import base64
import json
import os
import struct
import subprocess
import sys
import time
import wave

from dotenv import load_dotenv

load_dotenv()

# edge-tts 한국어 보이스 매핑 (Gemini 보이스 → edge-tts 보이스)
EDGE_TTS_VOICE_MAP = {
    "Kore": "ko-KR-InJoonNeural",       # 남성 차분한
    "Charon": "ko-KR-InJoonNeural",      # 남성 깊은
    "Fenrir": "ko-KR-InJoonNeural",      # 남성
    "Aoede": "ko-KR-SunHiNeural",        # 여성 부드러운
    "Leda": "ko-KR-SunHiNeural",         # 여성
    "Puck": "ko-KR-InJoonNeural",        # 남성
}
EDGE_TTS_DEFAULT = "ko-KR-SunHiNeural"


def get_client():
    """Gemini API 클라이언트 생성"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def generate_tts_edge(text, voice, output_path):
    """edge-tts로 TTS 생성 (오프라인 폴백)

    edge-tts는 mp3로 출력하므로 ffmpeg로 wav 변환
    """
    try:
        import edge_tts
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", "edge-tts"],
            capture_output=True, timeout=120,
        )
        import edge_tts

    # Gemini 보이스를 edge-tts 보이스로 매핑
    edge_voice = EDGE_TTS_VOICE_MAP.get(voice, EDGE_TTS_DEFAULT)

    mp3_path = output_path.replace(".wav", ".mp3")

    async def _generate():
        communicate = edge_tts.Communicate(text, edge_voice)
        await communicate.save(mp3_path)

    try:
        asyncio.run(_generate())
    except Exception as e:
        print(f"  [ERROR] edge-tts 생성 실패: {e}")
        return None

    if not os.path.exists(mp3_path):
        return None

    # mp3 → wav 변환 (ffmpeg)
    cmd = [
        "ffmpeg", "-y", "-i", mp3_path,
        "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # mp3 임시파일 삭제
    try:
        os.remove(mp3_path)
    except OSError:
        pass

    if result.returncode != 0:
        print(f"  [ERROR] mp3→wav 변환 실패: {result.stderr[:200]}")
        return None

    duration = get_wav_duration(output_path)
    return duration


def save_wave_file(filename, pcm_data, channels=1, rate=24000, sample_width=2):
    """PCM 데이터를 WAV 파일로 저장"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def get_wav_duration(filepath):
    """WAV 파일의 재생 길이(초)를 반환"""
    with wave.open(filepath, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def generate_tts(client, text, voice, model, style, output_path, retries=3):
    """단일 세그먼트 TTS 생성"""
    from google.genai import types

    # 나레이션 스타일 프롬프트 구성
    # 스타일 지시를 XML 태그로 감싸서 읽지 않게 분리
    if style:
        tts_prompt = (
            f"<speech_instructions>{style}</speech_instructions>\n\n"
            f"{text}"
        )
    else:
        tts_prompt = (
            f"<speech_instructions>"
            f"Speak naturally like a real person having a warm conversation. "
            f"Use natural breathing pauses between sentences. "
            f"Vary your pace slightly — slow down for emotional moments, "
            f"and maintain a gentle, soothing rhythm overall."
            f"</speech_instructions>\n\n"
            f"{text}"
        )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=tts_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice,
                            )
                        )
                    ),
                ),
            )

            audio_data = response.candidates[0].content.parts[0].inline_data.data
            if isinstance(audio_data, str):
                audio_data = base64.b64decode(audio_data)

            save_wave_file(output_path, audio_data)
            duration = get_wav_duration(output_path)
            return duration

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait = 2 ** (attempt + 1) * 5
                print(f"  [RATE_LIMIT] {wait}초 대기 후 재시도 ({attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                print(f"  [ERROR] TTS 생성 실패: {e} (시도 {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(3)

    return None


def main():
    parser = argparse.ArgumentParser(description="세그먼트별 TTS 나레이션 생성")
    parser.add_argument("--segments", required=True, help="segments.json 경로")
    parser.add_argument("--config", required=True, help="config.yaml 경로")
    parser.add_argument("--output", required=True, help="출력 디렉토리")
    parser.add_argument("--offline", action="store_true", help="오프라인 모드 (edge-tts 사용)")
    args = parser.parse_args()

    import yaml
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(args.segments, "r", encoding="utf-8") as f:
        segments = json.load(f)

    voice = config.get("TTS_VOICE", "Aoede")
    model = config.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
    style = config.get("TTS_STYLE", "")
    delay = config.get("TTS_DELAY", 2)

    os.makedirs(args.output, exist_ok=True)

    total = len(segments)
    success_count = 0
    fail_count = 0
    total_duration = 0.0

    if args.offline:
        edge_voice = EDGE_TTS_VOICE_MAP.get(voice, EDGE_TTS_DEFAULT)
        print(f"[Phase 3] edge-tts 생성 시작 ({total}개 세그먼트, 보이스: {edge_voice})")
    else:
        print(f"[Phase 3] TTS 생성 시작 ({total}개 세그먼트, 보이스: {voice})")

    client = None if args.offline else get_client()

    for i, seg in enumerate(segments):
        idx = i + 1
        output_path = os.path.join(args.output, f"tts_{idx:03d}.wav")

        if os.path.exists(output_path):
            duration = get_wav_duration(output_path)
            print(f"  [{idx}/{total}] 이미 존재: {output_path} ({duration:.1f}초)")
            seg["tts_path"] = output_path
            seg["duration"] = duration
            total_duration += duration
            success_count += 1
            continue

        text = seg.get("text", "")
        if not text.strip():
            print(f"  [{idx}/{total}] 빈 텍스트 - 건너뜀")
            fail_count += 1
            continue

        print(f"  [{idx}/{total}] TTS 생성 중: {text[:50]}...")

        if args.offline:
            duration = generate_tts_edge(text, voice, output_path)
        else:
            duration = generate_tts(client, text, voice, model, style, output_path)

        if duration is not None:
            seg["tts_path"] = output_path
            seg["duration"] = duration
            total_duration += duration
            success_count += 1
            print(f"  [{idx}/{total}] 완료: {duration:.1f}초")
        else:
            fail_count += 1
            print(f"  [{idx}/{total}] 실패")

        if not args.offline and i < total - 1:
            time.sleep(delay)

    # segments.json 업데이트
    with open(args.segments, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    engine = "edge-tts" if args.offline else "Gemini"
    print(f"\n[Phase 3] TTS 생성 완료 ({engine}): 성공 {success_count}, 실패 {fail_count}")
    print(f"  총 나레이션 길이: {total_duration:.1f}초 ({total_duration/60:.1f}분)")

    if fail_count > 0:
        print(f"[WARN] {fail_count}개 세그먼트의 TTS 생성에 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
