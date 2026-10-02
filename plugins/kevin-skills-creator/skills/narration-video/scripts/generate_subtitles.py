#!/usr/bin/env python3
"""세그먼트별 TTS 오디오 기반 SRT 자막 생성

두 가지 모드:
1. Gemini 오디오 이해 API로 정밀 타임스탬프 추출 (기본)
2. 세그먼트별 오디오 길이 기반 계산 (폴백)
"""

import argparse
import json
import os
import re
import sys
import time
import wave

from dotenv import load_dotenv

load_dotenv()


def get_client():
    """Gemini API 클라이언트 생성"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    from google import genai
    return genai.Client(api_key=api_key)


def get_wav_duration(filepath):
    """WAV 파일의 재생 길이(초)를 반환"""
    with wave.open(filepath, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def format_srt_time(seconds):
    """초를 SRT 타임스탬프 형식으로 변환 (HH:MM:SS,mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_text_for_subtitles(text, max_chars=40):
    """텍스트를 자막용 짧은 줄로 분할"""
    if len(text) <= max_chars:
        return [text]

    lines = []
    # 문장 부호 기준으로 먼저 분할
    sentences = re.split(r'(?<=[.!?。！？,，])\s*', text)

    current_line = ""
    for sentence in sentences:
        if not sentence.strip():
            continue
        if len(current_line) + len(sentence) <= max_chars:
            current_line += sentence
        else:
            if current_line:
                lines.append(current_line.strip())
            # 문장 자체가 max_chars보다 긴 경우
            if len(sentence) > max_chars:
                words = sentence.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_chars:
                        current_line += (" " + word if current_line else word)
                    else:
                        if current_line:
                            lines.append(current_line.strip())
                        current_line = word
            else:
                current_line = sentence

    if current_line.strip():
        lines.append(current_line.strip())

    return lines if lines else [text]


def generate_subtitles_gemini(client, segments, audio_dir, model, segment_gap=0.0, delay=2):
    """Gemini 오디오 이해 API로 세그먼트별 정밀 타임스탬프 추출"""
    from google.genai import types

    srt_entries = []
    cumulative_time = 0.0
    srt_index = 1

    total = len(segments)
    print(f"  Gemini 오디오 분석으로 타임스탬프 추출 ({total}개, 세그먼트 간격: {segment_gap}초)")

    for i, seg in enumerate(segments):
        idx = i + 1
        tts_path = seg.get("tts_path", os.path.join(audio_dir, f"tts_{idx:03d}.wav"))

        if not os.path.exists(tts_path):
            print(f"  [{idx}/{total}] 오디오 파일 없음: {tts_path}")
            continue

        duration = get_wav_duration(tts_path)
        text = seg.get("text", "")

        try:
            # Gemini에 오디오 업로드하여 타임스탬프 추출
            uploaded_file = client.files.upload(file=tts_path)

            prompt = (
                "이 오디오를 듣고 문장별 타임스탬프를 추출하세요. "
                "형식: [MM:SS.ss] 문장내용\n"
                "각 문장의 시작 시간을 정확히 기록하세요."
            )

            response = client.models.generate_content(
                model=model,
                contents=[prompt, uploaded_file],
            )

            result_text = response.text
            # 타임스탬프 파싱: [00:03.50] 문장 형태
            timestamp_pattern = r'\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*?)(?=\[|\Z)'
            matches = re.findall(timestamp_pattern, result_text, re.DOTALL)

            if matches:
                # 세그먼트 내 엔트리 수집 후 end 타임 체이닝
                seg_entries = []
                for m_min, m_sec, m_text in matches:
                    local_start = float(m_min) * 60 + float(m_sec)
                    line_text = m_text.strip()
                    if not line_text:
                        continue
                    seg_entries.append({
                        "local_start": local_start,
                        "text": line_text,
                    })

                # 시작 시간 순으로 정렬
                seg_entries.sort(key=lambda x: x["local_start"])

                # end 타임 체이닝: 다음 엔트리 시작 또는 세그먼트 오디오 끝
                for j, entry in enumerate(seg_entries):
                    start = cumulative_time + entry["local_start"]
                    if j + 1 < len(seg_entries):
                        end = cumulative_time + seg_entries[j + 1]["local_start"]
                    else:
                        end = cumulative_time + duration

                    srt_entries.append({
                        "index": srt_index,
                        "start": start,
                        "end": end,
                        "text": entry["text"],
                    })
                    srt_index += 1

                print(f"  [{idx}/{total}] Gemini 분석 완료: {len(seg_entries)}줄")
            else:
                # Gemini가 타임스탬프를 반환하지 않으면 폴백
                raise ValueError("타임스탬프 파싱 실패")

            # 업로드 파일 삭제
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

        except Exception as e:
            print(f"  [{idx}/{total}] Gemini 분석 실패, 폴백 사용: {e}")
            # 폴백: 텍스트를 균등 분할
            lines = split_text_for_subtitles(text)
            line_duration = duration / len(lines) if lines else duration

            for j, line in enumerate(lines):
                start = cumulative_time + j * line_duration
                end = cumulative_time + (j + 1) * line_duration
                srt_entries.append({
                    "index": srt_index,
                    "start": start,
                    "end": end,
                    "text": line,
                })
                srt_index += 1

        # 오디오 길이 + 세그먼트 간격을 누적 (영상에서 gap만큼 더 길어짐)
        cumulative_time += duration + segment_gap

        if i < total - 1:
            time.sleep(delay)

    return srt_entries, cumulative_time


def generate_subtitles_duration(segments, audio_dir, segment_gap=0.0):
    """세그먼트별 오디오 길이 기반 자막 생성 (폴백)"""
    srt_entries = []
    cumulative_time = 0.0
    srt_index = 1

    total = len(segments)
    print(f"  오디오 길이 기반 자막 생성 ({total}개, 세그먼트 간격: {segment_gap}초)")

    for i, seg in enumerate(segments):
        idx = i + 1
        tts_path = seg.get("tts_path", os.path.join(audio_dir, f"tts_{idx:03d}.wav"))

        if not os.path.exists(tts_path):
            print(f"  [{idx}/{total}] 오디오 파일 없음: {tts_path}")
            continue

        duration = get_wav_duration(tts_path)
        text = seg.get("text", "")

        lines = split_text_for_subtitles(text)
        line_duration = duration / len(lines) if lines else duration

        for j, line in enumerate(lines):
            start = cumulative_time + j * line_duration
            end = cumulative_time + (j + 1) * line_duration

            srt_entries.append({
                "index": srt_index,
                "start": start,
                "end": end,
                "text": line,
            })
            srt_index += 1

        # 오디오 길이 + 세그먼트 간격을 누적
        cumulative_time += duration + segment_gap

    return srt_entries, cumulative_time


def write_srt(entries, output_path):
    """SRT 파일 작성"""
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n")
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="TTS 오디오 기반 SRT 자막 생성")
    parser.add_argument("--segments", required=True, help="segments.json 경로")
    parser.add_argument("--audio-dir", required=True, help="TTS 오디오 디렉토리")
    parser.add_argument("--output", required=True, help="SRT 출력 경로")
    parser.add_argument("--mode", choices=["gemini", "duration"], default="gemini",
                        help="타임스탬프 추출 모드 (기본: gemini)")
    parser.add_argument("--config", help="config.yaml 경로")
    args = parser.parse_args()

    with open(args.segments, "r", encoding="utf-8") as f:
        segments = json.load(f)

    model = "gemini-2.5-flash"
    segment_gap = 0.0
    if args.config:
        import yaml
        with open(args.config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        model = config.get("AUDIO_MODEL", model)
        segment_gap = config.get("SEGMENT_GAP", 0.0)

    print(f"[Phase 4] 자막 생성 시작 (모드: {args.mode})")

    if args.mode == "gemini":
        client = get_client()
        entries, total_duration = generate_subtitles_gemini(
            client, segments, args.audio_dir, model, segment_gap=segment_gap
        )
    else:
        entries, total_duration = generate_subtitles_duration(
            segments, args.audio_dir, segment_gap=segment_gap
        )

    write_srt(entries, args.output)

    print(f"\n[Phase 4] 자막 생성 완료")
    print(f"  자막 수: {len(entries)}개")
    print(f"  총 길이: {total_duration:.1f}초 ({total_duration/60:.1f}분)")
    print(f"  출력: {args.output}")


if __name__ == "__main__":
    main()
