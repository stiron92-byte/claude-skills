#!/usr/bin/env python3
"""FFmpeg를 사용한 세그먼트별 이미지+오디오+자막 영상 합성"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import wave

from dotenv import load_dotenv

load_dotenv()


def get_wav_duration(filepath):
    """WAV 파일의 재생 길이(초)를 반환"""
    with wave.open(filepath, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def check_ffmpeg():
    """FFmpeg 설치 확인"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def find_korean_font():
    """시스템에서 한글 폰트 경로 탐색"""
    font_candidates = [
        # macOS
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        "/Library/Fonts/NotoSansCJKkr-Regular.otf",
        # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for font in font_candidates:
        if os.path.exists(font):
            return font

    # fc-list로 검색
    try:
        result = subprocess.run(
            ["fc-list", ":lang=ko", "file"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            first_font = result.stdout.strip().split("\n")[0].split(":")[0].strip()
            if os.path.exists(first_font):
                return first_font
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def create_segment_video(img_path, audio_path, output_path, resolution, fps, segment_gap=0.0):
    """단일 세그먼트의 정지 이미지 + 오디오 영상 생성 (gap 포함)"""
    width, height = resolution.split("x")

    # 오디오 길이 + gap으로 영상 총 길이 결정
    audio_duration = get_wav_duration(audio_path)
    total_duration = audio_duration + segment_gap

    # gap이 있으면 오디오 끝에 무음 패딩 추가
    if segment_gap > 0:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-i", audio_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "-af", f"apad=whole_dur={total_duration}",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-t", str(total_duration),
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-i", audio_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-shortest",
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  [ERROR] FFmpeg 세그먼트 생성 실패: {result.stderr[:500]}")
        return False
    return True


def concat_videos_with_fade(segment_videos, output_path, fade_duration, fps):
    """세그먼트 영상들을 crossfade로 결합"""
    if len(segment_videos) == 1:
        # 세그먼트가 1개면 그대로 복사
        cmd = ["ffmpeg", "-y", "-i", segment_videos[0], "-c", "copy", output_path]
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return True

    # 2개 이상: concat demuxer 사용 (fade는 xfade 필터로)
    # xfade 필터 체이닝이 복잡하므로, 간단한 접근: 각 세그먼트에 fade-in/out 적용 후 concat
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, dir=os.path.dirname(output_path)
    ) as f:
        fade_list_path = f.name
        for vid in segment_videos:
            f.write(f"file '{os.path.abspath(vid)}'\n")

    # 각 세그먼트에 fade 적용
    faded_videos = []
    for i, vid in enumerate(segment_videos):
        faded_path = vid.replace(".mp4", "_faded.mp4")

        # 영상 길이 확인
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", vid
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        try:
            vid_duration = float(probe.stdout.strip())
        except (ValueError, AttributeError):
            vid_duration = 10.0

        fade_out_start = max(0, vid_duration - fade_duration)

        vf_parts = []
        if i > 0:  # 첫 번째가 아니면 fade-in
            vf_parts.append(f"fade=t=in:st=0:d={fade_duration}")
        if i < len(segment_videos) - 1:  # 마지막이 아니면 fade-out
            vf_parts.append(f"fade=t=out:st={fade_out_start}:d={fade_duration}")

        af_parts = []
        if i > 0:
            af_parts.append(f"afade=t=in:st=0:d={fade_duration}")
        if i < len(segment_videos) - 1:
            af_parts.append(f"afade=t=out:st={fade_out_start}:d={fade_duration}")

        if vf_parts or af_parts:
            cmd = ["ffmpeg", "-y", "-i", vid]
            if vf_parts:
                cmd += ["-vf", ",".join(vf_parts)]
            if af_parts:
                cmd += ["-af", ",".join(af_parts)]
            cmd += ["-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", faded_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                faded_videos.append(faded_path)
            else:
                faded_videos.append(vid)
        else:
            faded_videos.append(vid)

    # concat demuxer로 결합
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, dir=os.path.dirname(output_path)
    ) as f:
        concat_list_path = f.name
        for vid in faded_videos:
            f.write(f"file '{os.path.abspath(vid)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    # 임시 파일 정리
    try:
        os.unlink(fade_list_path)
        os.unlink(concat_list_path)
        for vid in faded_videos:
            if vid.endswith("_faded.mp4") and os.path.exists(vid):
                os.unlink(vid)
    except OSError:
        pass

    if result.returncode != 0:
        print(f"  [ERROR] concat 실패: {result.stderr[:500]}")
        return False
    return True


def add_subtitles(input_video, srt_path, output_path, font_path, font_size):
    """영상에 SRT 자막 오버레이"""
    if font_path:
        # force_style로 폰트 지정
        subtitle_filter = (
            f"subtitles={srt_path}:force_style="
            f"'FontName=NotoSansCJK,FontSize={font_size},"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"Outline=2,Shadow=1,MarginV=50'"
        )
    else:
        subtitle_filter = (
            f"subtitles={srt_path}:force_style="
            f"'FontSize={font_size},"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"Outline=2,Shadow=1,MarginV=50'"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"  [WARN] 자막 오버레이 실패: {result.stderr[:300]}")
        return False
    return True


def mix_bgm(input_video, bgm_path, bgm_volume, output_path):
    """BGM 믹싱"""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-stream_loop", "-1",
        "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={bgm_volume}[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"  [WARN] BGM 믹싱 실패: {result.stderr[:300]}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="세그먼트별 영상 합성")
    parser.add_argument("--segments", required=True, help="segments.json 경로")
    parser.add_argument("--media-dir", required=True, help="이미지/오디오 디렉토리")
    parser.add_argument("--srt", required=True, help="SRT 자막 경로")
    parser.add_argument("--config", required=True, help="config.yaml 경로")
    parser.add_argument("--output", required=True, help="출력 영상 경로")
    parser.add_argument("--bgm", default=None, help="BGM 파일 경로")
    args = parser.parse_args()

    if not check_ffmpeg():
        print("[ERROR] FFmpeg가 설치되지 않았습니다. setup.sh를 실행하세요.")
        sys.exit(1)

    import yaml
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(args.segments, "r", encoding="utf-8") as f:
        segments = json.load(f)

    resolution = config.get("RESOLUTION", "1920x1080")
    fps = config.get("FPS", 30)
    fade_duration = config.get("FADE_DURATION", 1.0)
    segment_gap = config.get("SEGMENT_GAP", 0.5)
    bgm_volume = config.get("BGM_VOLUME", 0.15)
    font_size = config.get("FONT_SIZE", 24)

    bgm_path = args.bgm or os.environ.get("BGM_PATH")

    # 자동 생성된 BGM 파일 자동 탐지
    if not bgm_path:
        auto_bgm = os.path.join(os.path.dirname(args.segments), "bgm_auto.m4a")
        if os.path.exists(auto_bgm):
            bgm_path = auto_bgm
            print(f"[INFO] 자동 생성 BGM 감지: {bgm_path}")

    font_path = find_korean_font()
    if font_path:
        print(f"[INFO] 한글 폰트: {font_path}")
    else:
        print("[WARN] 한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")

    total = len(segments)
    print(f"[Phase 5] 영상 합성 시작 ({total}개 세그먼트, 세그먼트 간격: {segment_gap}초)")

    # --- Step 1: 세그먼트별 영상 생성 ---
    segment_videos = []
    temp_dir = tempfile.mkdtemp(prefix="narration_")

    for i, seg in enumerate(segments):
        idx = i + 1
        img_path = seg.get("image_path", os.path.join(args.media_dir, f"img_{idx:03d}.png"))
        audio_path = seg.get("tts_path", os.path.join(args.media_dir, f"tts_{idx:03d}.wav"))

        if not os.path.exists(img_path):
            print(f"  [{idx}/{total}] 이미지 없음: {img_path} - 건너뜀")
            continue
        if not os.path.exists(audio_path):
            print(f"  [{idx}/{total}] 오디오 없음: {audio_path} - 건너뜀")
            continue

        seg_video = os.path.join(temp_dir, f"seg_{idx:03d}.mp4")
        print(f"  [{idx}/{total}] 세그먼트 영상 생성 중...")

        if create_segment_video(img_path, audio_path, seg_video, resolution, fps, segment_gap):
            segment_videos.append(seg_video)
            print(f"  [{idx}/{total}] 완료")
        else:
            print(f"  [{idx}/{total}] 실패")

    if not segment_videos:
        print("[ERROR] 생성된 세그먼트 영상이 없습니다.")
        sys.exit(1)

    # --- Step 2: 세그먼트 결합 (fade 전환) ---
    print(f"  세그먼트 결합 중 ({len(segment_videos)}개)...")
    concat_output = os.path.join(temp_dir, "concat.mp4")
    if not concat_videos_with_fade(segment_videos, concat_output, fade_duration, fps):
        print("[ERROR] 세그먼트 결합 실패")
        sys.exit(1)
    print("  세그먼트 결합 완료")

    # --- Step 3: 자막 오버레이 ---
    current_video = concat_output
    if os.path.exists(args.srt) and os.path.getsize(args.srt) > 0:
        print("  자막 오버레이 적용 중...")
        subtitled_output = os.path.join(temp_dir, "subtitled.mp4")
        if add_subtitles(current_video, args.srt, subtitled_output, font_path, font_size):
            current_video = subtitled_output
            print("  자막 오버레이 완료")
        else:
            print("  자막 오버레이 건너뜀 (폰트 문제 가능)")
    else:
        print("  자막 파일 없음 - 건너뜀")

    # --- Step 4: BGM 믹싱 ---
    if bgm_path and os.path.exists(bgm_path):
        print(f"  BGM 믹싱 중 (볼륨: {bgm_volume})...")
        bgm_output = os.path.join(temp_dir, "with_bgm.mp4")
        if mix_bgm(current_video, bgm_path, bgm_volume, bgm_output):
            current_video = bgm_output
            print("  BGM 믹싱 완료")
        else:
            print("  BGM 믹싱 건너뜀")
    else:
        if bgm_path:
            print(f"  [WARN] BGM 파일 없음: {bgm_path}")
        else:
            print("  BGM 없이 진행")

    # --- Step 5: 최종 출력 ---
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    # 최종 파일 복사
    cmd = ["ffmpeg", "-y", "-i", current_video, "-c", "copy", args.output]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"[ERROR] 최종 출력 실패: {result.stderr[:300]}")
        sys.exit(1)

    # --- 임시 파일 정리 ---
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except OSError:
        pass

    # --- 결과 출력 ---
    file_size = os.path.getsize(args.output)
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", args.output
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
    try:
        final_duration = float(probe.stdout.strip())
    except (ValueError, AttributeError):
        final_duration = 0

    print(f"\n[Phase 5] 영상 합성 완료")
    print(f"  출력: {args.output}")
    print(f"  길이: {final_duration:.1f}초 ({final_duration/60:.1f}분)")
    print(f"  크기: {file_size / 1024 / 1024:.1f}MB")
    print(f"  해상도: {resolution}, {fps}fps")


if __name__ == "__main__":
    main()
