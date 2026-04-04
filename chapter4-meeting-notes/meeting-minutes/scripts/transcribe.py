#!/usr/bin/env python3
"""
faster-whisper 기반 음성 → 텍스트 변환 스크립트

사용법:
  python transcribe.py --input <음성파일> --output <출력텍스트파일> [--language ko] [--model base]

지원 포맷: .mp3, .wav, .m4a, .webm, .ogg
기본 모델: base (속도 우선)
한국어 정확도 필요 시: --model small
"""

import argparse
import os
import sys
import time


SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}

MAX_FILE_SIZE_MB = 50


def format_timestamp(seconds: float) -> str:
    """초 단위 시간을 HH:MM:SS 형태로 변환한다."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def validate_input(input_path: str) -> None:
    """입력 파일의 존재 여부, 포맷, 크기를 검증한다."""
    if not os.path.exists(input_path):
        print(f"[오류] 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        print(
            f"[오류] 지원하지 않는 파일 형식입니다: {ext}\n"
            f"지원 형식: {', '.join(sorted(SUPPORTED_FORMATS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        print(
            f"[오류] 파일 크기가 너무 큽니다: {file_size_mb:.1f}MB (최대 {MAX_FILE_SIZE_MB}MB)\n"
            f"대안: (1) 노션 녹음 기능으로 텍스트 변환 후 붙여넣기\n"
            f"      (2) Clova Note 등 외부 STT 서비스 이용\n"
            f"      (3) 녹음 파일을 30분 단위로 분할 후 업로드",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[정보] 파일: {os.path.basename(input_path)} ({file_size_mb:.1f}MB)")


def estimate_duration(input_path: str) -> str:
    """파일 크기 기반으로 예상 처리 시간을 반환한다."""
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    if file_size_mb <= 10:
        return "1~2분"
    elif file_size_mb <= 25:
        return "2~5분"
    else:
        return "5~10분"


def transcribe(input_path: str, output_path: str, language: str, model_size: str) -> None:
    """faster-whisper를 사용하여 음성 파일을 텍스트로 변환한다."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "[오류] faster-whisper가 설치되지 않았습니다.\n"
            "설치 명령: pip install faster-whisper --break-system-packages",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[정보] 모델 로딩 중: {model_size} (최초 실행 시 다운로드가 필요합니다)")
    start_time = time.time()

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    load_time = time.time() - start_time
    print(f"[정보] 모델 로딩 완료 ({load_time:.1f}초)")

    lang_param = None if language == "auto" else language
    print(f"[정보] 트랜스크립션 시작 (언어: {language})")
    print(f"[정보] 예상 소요 시간: {estimate_duration(input_path)}")

    segments, info = model.transcribe(
        input_path,
        language=lang_param,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    if lang_param is None:
        print(f"[정보] 감지된 언어: {info.language} (확률: {info.language_probability:.2%})")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    segment_count = 0
    total_duration = 0.0

    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            start_ts = format_timestamp(segment.start)
            end_ts = format_timestamp(segment.end)
            text = segment.text.strip()

            if text:
                line = f"[{start_ts} ~ {end_ts}] {text}"
                f.write(line + "\n")
                segment_count += 1
                total_duration = segment.end

                if segment_count % 10 == 0:
                    print(f"[진행] {segment_count}개 세그먼트 처리 완료 (현재 위치: {end_ts})")

    elapsed = time.time() - start_time
    print(f"\n[완료] 트랜스크립션 완료!")
    print(f"  - 세그먼트 수: {segment_count}개")
    print(f"  - 음성 길이: {format_timestamp(total_duration)}")
    print(f"  - 처리 시간: {elapsed:.1f}초")
    print(f"  - 출력 파일: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="faster-whisper 기반 음성 → 텍스트 변환 스크립트"
    )
    parser.add_argument(
        "--input", required=True, help="입력 음성 파일 경로 (.mp3, .wav, .m4a, .webm, .ogg)"
    )
    parser.add_argument(
        "--output", required=True, help="출력 텍스트 파일 경로"
    )
    parser.add_argument(
        "--language",
        default="ko",
        choices=["ko", "en", "auto"],
        help="음성 언어 (기본값: ko). auto는 자동 감지",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["base", "small"],
        help="Whisper 모델 크기 (기본값: base). 정확도가 필요하면 small 사용",
    )

    args = parser.parse_args()

    validate_input(args.input)
    transcribe(args.input, args.output, args.language, args.model)


if __name__ == "__main__":
    main()
