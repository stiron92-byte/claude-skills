#!/usr/bin/env python3
"""
전체 파이프라인 오케스트레이터
Phase 0 (환경 설정) -> Phase 1 (자막 추출) -> Phase 2 (하이라이트 선별) ->
Phase 3 (쇼츠 생성) -> Phase 4 (결과 보고)

사용법:
  python3 scripts/run_pipeline.py --url "https://youtube.com/watch?v=..." --count 10 --lang ko
"""

import argparse
import json
import os
import subprocess
import sys
import time


def run_phase(phase_name: str, cmd: list, timeout: int = 300) -> bool:
    """단일 Phase 실행 + 에러 처리"""
    print(f"\n{'='*60}")
    print(f"  {phase_name}")
    print(f"{'='*60}")
    print(f"  CMD: {' '.join(cmd)}")
    print()

    start_time = time.time()
    try:
        result = subprocess.run(cmd, timeout=timeout)
        elapsed = time.time() - start_time

        if result.returncode == 0:
            print(f"\n  [{phase_name}] 완료 ({elapsed:.0f}초)")
            return True
        else:
            print(f"\n  [{phase_name}] 실패 (exit code: {result.returncode}, {elapsed:.0f}초)")
            return False

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"\n  [{phase_name}] 타임아웃 ({elapsed:.0f}초)")
        return False
    except FileNotFoundError as e:
        print(f"\n  [{phase_name}] 명령을 찾을 수 없음: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Shorts 자동 생성 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python3 scripts/run_pipeline.py --url "https://youtube.com/watch?v=ABC123" --count 10
  python3 scripts/run_pipeline.py --url "https://youtube.com/watch?v=ABC123" --count 5 --lang en
  python3 scripts/run_pipeline.py --url "https://youtube.com/watch?v=ABC123" --skip-setup
        """
    )
    parser.add_argument("--url", required=True, help="YouTube URL")
    parser.add_argument("--count", type=int, default=10, help="생성할 쇼츠 수 (기본: 10)")
    parser.add_argument("--lang", default="ko", help="자막 언어 (기본: ko)")
    parser.add_argument("--output", default="output", help="출력 디렉토리 (기본: output)")
    parser.add_argument("--skip-setup", action="store_true", help="Phase 0 (환경 설정) 건너뛰기")
    parser.add_argument("--skip-subtitles", action="store_true", help="Phase 1 (자막 추출) 건너뛰기 (이미 추출된 경우)")
    parser.add_argument("--skip-highlights", action="store_true", help="Phase 2 (하이라이트 선별) 건너뛰기 (이미 선별된 경우)")
    args = parser.parse_args()

    output_dir = args.output
    shorts_dir = os.path.join(output_dir, "shorts")
    os.makedirs(shorts_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)

    # 스크립트 디렉토리 기준으로 경로 결정
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("  YouTube Shorts 자동 생성 파이프라인")
    print("=" * 60)
    print(f"  URL:    {args.url}")
    print(f"  쇼츠:   {args.count}개")
    print(f"  언어:   {args.lang}")
    print(f"  출력:   {output_dir}/")

    pipeline_start = time.time()
    phase_results = {}

    # --- Phase 0: 환경 설정 ---
    if not args.skip_setup:
        setup_script = os.path.join(script_dir, "setup.sh")
        ok = run_phase("Phase 0: 환경 설정", ["bash", setup_script])
        phase_results["setup"] = ok
        if not ok:
            print("\n환경 설정 실패. --skip-setup으로 건너뛸 수 있습니다.")
            sys.exit(1)
    else:
        print("\n[Phase 0: 환경 설정] 건너뜀 (--skip-setup)")
        phase_results["setup"] = True

    # --- Phase 1: 자막 추출 ---
    transcript_json = os.path.join(output_dir, "transcript.json")

    if not args.skip_subtitles:
        extract_script = os.path.join(script_dir, "extract_subtitles.py")
        ok = run_phase("Phase 1: 자막 추출", [
            "python3", extract_script,
            "--url", args.url,
            "--output", output_dir,
            "--lang", args.lang,
        ], timeout=120)
        phase_results["subtitles"] = ok
        if not ok:
            print("\n자막 추출 실패. 자막이 없는 영상이거나 봇 감지일 수 있습니다.")
            print("상세 로그: output/logs/")
            sys.exit(1)
    else:
        print("\n[Phase 1: 자막 추출] 건너뜀 (--skip-subtitles)")
        phase_results["subtitles"] = True

    if not os.path.exists(transcript_json):
        print(f"\nERROR: {transcript_json}을 찾을 수 없습니다.")
        sys.exit(1)

    # --- Phase 2: 하이라이트 선별 ---
    highlights_json = os.path.join(output_dir, "highlights.json")

    if not args.skip_highlights:
        select_script = os.path.join(script_dir, "select_highlights.py")
        ok = run_phase("Phase 2: 하이라이트 선별", [
            "python3", select_script,
            "--transcript", transcript_json,
            "--output", highlights_json,
            "--count", str(args.count),
            "--lang", args.lang,
        ], timeout=60)
        phase_results["highlights"] = ok
        if not ok:
            print("\n하이라이트 선별 실패.")
            sys.exit(1)
    else:
        print("\n[Phase 2: 하이라이트 선별] 건너뜀 (--skip-highlights)")
        phase_results["highlights"] = True

    if not os.path.exists(highlights_json):
        print(f"\nERROR: {highlights_json}을 찾을 수 없습니다.")
        sys.exit(1)

    # --- Phase 3: 쇼츠 생성 ---
    generate_script = os.path.join(script_dir, "generate_shorts.py")
    srt_path = os.path.join(output_dir, "transcript.srt")

    generate_cmd = [
        "python3", generate_script,
        "--highlights", highlights_json,
        "--url", args.url,
        "--output", shorts_dir,
    ]
    if os.path.exists(srt_path):
        generate_cmd.extend(["--srt", srt_path])

    ok = run_phase("Phase 3: 쇼츠 생성", generate_cmd, timeout=1800)
    phase_results["generate"] = ok

    # --- Phase 4: 결과 보고 ---
    pipeline_elapsed = time.time() - pipeline_start

    print(f"\n{'='*60}")
    print(f"  Phase 4: 결과 보고")
    print(f"{'='*60}")

    metadata_path = os.path.join(shorts_dir, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        shorts = metadata.get("shorts", metadata) if isinstance(metadata, dict) else metadata
        if isinstance(shorts, dict):
            shorts = shorts.get("shorts", [])
        failures = metadata.get("failures", []) if isinstance(metadata, dict) else []

        total_size = sum(s.get("size_mb", 0) for s in shorts)
        total_duration = sum(s.get("duration", 0) for s in shorts)

        print(f"\n  생성 성공: {len(shorts)}개")
        if failures:
            print(f"  생성 실패: {len(failures)}개")
        print(f"  총 용량:   {total_size:.1f}MB")
        print(f"  총 길이:   {total_duration:.0f}초")
        print(f"  소요 시간: {pipeline_elapsed:.0f}초 ({pipeline_elapsed/60:.1f}분)")
        print()

        for s in shorts:
            print(f"  [{s.get('index', '?'):02d}] {s.get('title', '')} - {s.get('duration', 0):.0f}s ({s.get('size_mb', 0):.1f}MB)")

        if failures:
            print(f"\n  실패 목록:")
            for f_item in failures:
                print(f"  [{f_item.get('index', '?'):02d}] {f_item.get('title', '')} - {f_item.get('reason', '')}")

        print(f"\n  메타데이터: {metadata_path}")
        print(f"  에러 로그:  output/logs/")
    else:
        print("\n  메타데이터 파일을 찾을 수 없습니다.")
        print(f"  쇼츠 생성 {'성공' if phase_results.get('generate') else '실패'}")

    # Phase 요약
    print(f"\n{'='*60}")
    print(f"  Phase 요약")
    print(f"{'='*60}")
    for phase, ok in phase_results.items():
        status = "성공" if ok else "실패"
        print(f"  {phase:15s} : {status}")
    print(f"  총 소요 시간    : {pipeline_elapsed:.0f}초")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
