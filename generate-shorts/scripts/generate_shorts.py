#!/usr/bin/env python3
"""
쇼츠 영상 자동 편집
- 하이라이트 구간만 개별 다운로드 (전체 영상 다운로드 X)
- 컨테이너 환경 자동 감지 (쿠키 조건부)
- 한글 폰트 자동 탐색 + fontfile 명시
- 파일명 불일치 glob 처리
- concat filter 사용 (코덱 불일치 방지)
- 에러 발생 시 output/logs/에 상세 로그
"""

import argparse
import glob
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time


# --- 봇 감지 우회 ---

USER_AGENTS = {
    "Darwin": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Linux": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

MAX_RETRIES = 3
BASE_DELAY = 2
MAX_DELAY = 5


def get_user_agent() -> str:
    return USER_AGENTS.get(platform.system(), USER_AGENTS["Linux"])


def is_container_env() -> bool:
    if os.environ.get("CLAUDE_CONTAINER") == "1":
        return True
    if os.path.isdir("/home/claude"):
        return True
    if os.path.exists("/.dockerenv"):
        return True
    return False


def get_cookie_browser() -> str | None:
    if is_container_env():
        return None
    return os.environ.get("YT_COOKIE_BROWSER", "chrome")


def get_cookie_file() -> str | None:
    for c in ["cookies.txt", "output/cookies.txt", os.path.expanduser("~/cookies.txt")]:
        if os.path.exists(c):
            return c
    return None


def get_proxy() -> str | None:
    return os.environ.get("YT_PROXY")


def random_delay():
    time.sleep(random.uniform(BASE_DELAY, MAX_DELAY))


def build_ytdlp_base_args(use_cookies: bool = False) -> list:
    """yt-dlp 공통 인자. use_cookies=True는 봇 감지 실패 시 재시도용"""
    args = [
        "yt-dlp",
        "--user-agent", get_user_agent(),
    ]
    # 쿠키: 명시적으로 요청된 경우에만 (키체인 팝업 방지)
    if use_cookies:
        cookie_file = get_cookie_file()
        if cookie_file:
            args.extend(["--cookies", cookie_file])
        elif not is_container_env():
            cookie_browser = get_cookie_browser()
            if cookie_browser:
                args.extend(["--cookies-from-browser", cookie_browser])
    proxy = get_proxy()
    if proxy:
        args.extend(["--proxy", proxy])
    return args


# --- 한글 폰트 ---

def get_font_path() -> str | None:
    """한글 지원 폰트 경로 탐색"""
    candidates = [
        # Linux (Noto Sans CJK)
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        # Linux (Nanum)
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        # macOS
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ]
    for f in candidates:
        if os.path.exists(f):
            return f
    # fc-list로 탐색 시도
    try:
        result = subprocess.run(
            ["fc-list", ":lang=ko", "-f", "%{file}\n"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


# --- 에러 로깅 ---

def log_error(description: str, cmd: list, result) -> str:
    log_dir = "output/logs"
    os.makedirs(log_dir, exist_ok=True)
    safe_desc = re.sub(r'[^\w\-]', '_', description)
    log_path = os.path.join(log_dir, f"error_{safe_desc}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"CMD: {' '.join(cmd)}\n\n")
        f.write(f"RETURNCODE: {result.returncode}\n\n")
        f.write(f"STDOUT:\n{result.stdout}\n\n")
        f.write(f"STDERR:\n{result.stderr}\n")
    return log_path


def run_cmd(cmd: list, description: str = "", timeout: int = 120):
    """통합 명령 실행 + 에러 로깅"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            log_path = log_error(description, cmd, result)
            print(f"    {description} 실패 - 로그: {log_path}")
        return result
    except subprocess.TimeoutExpired:
        print(f"    {description} 타임아웃 ({timeout}초)")
        return None


# --- 영상 정보 ---

def get_video_info(video_path: str) -> dict:
    """영상의 해상도, fps 정보 추출"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                fps_str = stream.get("r_frame_rate", "30/1")
                parts = fps_str.split("/")
                fps = int(parts[0]) / int(parts[1]) if len(parts) == 2 and int(parts[1]) != 0 else 30
                return {
                    "width": int(stream.get("width", 1080)),
                    "height": int(stream.get("height", 1920)),
                    "fps": round(fps, 2),
                }
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return {"width": 1080, "height": 1920, "fps": 30}


def get_duration(video_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


# --- 다운로드 ---

def download_section(url: str, start: float, end: float, output_path: str) -> bool:
    """구간 다운로드: 쿠키 없이 먼저 -> 실패 시 쿠키 재시도 + 파일명 glob"""
    section_spec = f"*{start}-{end}"

    for attempt in range(MAX_RETRIES):
        use_cookies = attempt > 0  # 첫 시도는 쿠키 없이
        if attempt > 0:
            backoff = BASE_DELAY * (2 ** attempt) + random.uniform(0, 2)
            print(f"    재시도 {attempt + 1}/{MAX_RETRIES} ({'쿠키 포함, ' if use_cookies else ''}{backoff:.0f}초 대기)...")
            time.sleep(backoff)

        cmd = build_ytdlp_base_args(use_cookies=use_cookies) + [
            "--download-sections", section_spec,
            "-f", "bestvideo[height<=1080]+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_path,
            "--force-keyframes-at-cuts",
            url
        ]

        result = run_cmd(cmd, f"download_s{start:.0f}_e{end:.0f}", timeout=180)
        if result is None:
            continue

        # 파일 존재 확인 (정확한 경로)
        if os.path.exists(output_path):
            random_delay()
            return True

        # yt-dlp가 다른 이름으로 저장했을 수 있음 (문제 6)
        base = os.path.splitext(output_path)[0]
        candidates = glob.glob(f"{base}*")
        if candidates:
            actual = candidates[0]
            os.rename(actual, output_path)
            random_delay()
            return True

        if result.returncode != 0:
            stderr_lower = result.stderr.lower()
            if "sign in" in stderr_lower or "bot" in stderr_lower:
                print(f"    봇 감지 - 쿠키 확인 필요")

    return False


# --- 자막 추출 ---

def extract_srt_for_section(full_srt_path: str, start: float, end: float, output_srt: str):
    """전체 SRT에서 구간 자막 추출 + offset 조정"""
    if not os.path.exists(full_srt_path):
        with open(output_srt, "w", encoding="utf-8") as f:
            f.write("")
        return

    with open(full_srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    filtered = []
    idx = 1

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        time_line = lines[1]
        if " --> " not in time_line:
            continue

        start_str, end_str = time_line.split(" --> ")
        seg_start = _parse_srt_time(start_str.strip())
        seg_end = _parse_srt_time(end_str.strip())

        if seg_end > start and seg_start < end:
            adj_start = max(0, seg_start - start)
            adj_end = seg_end - start
            text = "\n".join(lines[2:])
            filtered.append(f"{idx}\n{_fmt_time(adj_start)} --> {_fmt_time(adj_end)}\n{text}")
            idx += 1

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n\n".join(filtered))


def _parse_srt_time(time_str: str) -> float:
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# --- 텍스트 오버레이 ---

def create_text_overlay(
    text: str, duration: float, width: int, height: int,
    output_path: str, font_size: int = 48, fps: float = 30,
    bg_color: str = "black"
):
    """텍스트 오버레이 영상 (한글 폰트 지정, fps 맞춤)"""
    safe_text = text.replace("'", "'\\''").replace(":", "\\:").replace("\\", "\\\\")

    font_path = get_font_path()
    fontfile_opt = f":fontfile='{font_path}'" if font_path else ""

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={width}x{height}:d={duration}:r={fps}",
        "-f", "lavfi",
        "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(duration),
        "-vf", (
            f"drawtext=text='{safe_text}':"
            f"fontsize={font_size}:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"borderw=2:bordercolor=black"
            f"{fontfile_opt}"
        ),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    result = run_cmd(cmd, f"overlay_{os.path.basename(output_path)}")
    return result is not None and result.returncode == 0


# --- 쇼츠 처리 ---

def process_short(
    index: int, highlight: dict, url: str,
    output_dir: str, srt_path: str, config: dict
) -> dict | None:
    """단일 쇼츠 영상 처리"""
    start = highlight["start"]
    end = highlight["end"]
    title = highlight.get("title", f"Short {index}")
    hook = highlight.get("hook", "")
    duration = end - start

    print(f"\n--- Short {index:02d}: {title} [{start:.1f}s - {end:.1f}s] ({duration:.0f}s) ---")

    width = config.get("width", 1080)
    height = config.get("height", 1920)
    intro_duration = config.get("intro_duration", 2)
    outro_duration = config.get("outro_duration", 2)
    outro_text = config.get("outro_text", "구독과 좋아요 부탁드립니다!")
    font_size = config.get("subtitle_font_size", 28)
    border_width = config.get("subtitle_border_width", 2)

    font_path = get_font_path()

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = os.path.join(tmpdir, f"raw_{index:02d}.mp4")
        # SRT를 심플한 이름으로 (문제 9: 특수문자 방지)
        section_srt = os.path.join(tmpdir, f"sub.srt")
        cropped_path = os.path.join(tmpdir, f"cropped.mp4")
        intro_path = os.path.join(tmpdir, f"intro.mp4")
        outro_path = os.path.join(tmpdir, f"outro.mp4")
        final_path = os.path.join(output_dir, f"short_{index:02d}.mp4")

        # 1. 구간 다운로드
        print(f"  1/4 구간 다운로드 중...")
        if not download_section(url, start, end, raw_path):
            print(f"  건너뜀: 다운로드 실패")
            return None

        # 본편 영상 정보 추출 (문제 8: fps 맞춤)
        video_info = get_video_info(raw_path)
        fps = video_info["fps"]

        # 2. 자막 추출
        print(f"  2/4 자막 추출 중...")
        extract_srt_for_section(srt_path, start, end, section_srt)

        # 3. 세로 크롭 + 자막
        print(f"  3/4 세로 크롭 + 자막 합성 중...")
        subtitle_filter = ""
        if os.path.exists(section_srt) and os.path.getsize(section_srt) > 0:
            # SRT를 tmpdir 내 심플 이름으로 복사 (경로 특수문자 이슈 방지)
            safe_srt = section_srt.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
            font_name_opt = ""
            if font_path:
                font_basename = os.path.basename(font_path).replace(".ttc", "").replace(".ttf", "")
                font_name_opt = f",FontName={font_basename}"
            subtitle_filter = (
                f",subtitles='{safe_srt}':"
                f"force_style='FontSize={font_size},"
                f"PrimaryColour=&H00FFFFFF,"
                f"OutlineColour=&H00000000,"
                f"BorderStyle=3,Outline={border_width},"
                f"Alignment=2,MarginV=80"
                f"{font_name_opt}'"
            )

        crop_cmd = [
            "ffmpeg", "-y", "-i", raw_path,
            "-vf", (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}"
                f"{subtitle_filter}"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            cropped_path
        ]
        result = run_cmd(crop_cmd, f"crop_short{index:02d}")

        if result is None or result.returncode != 0:
            # 자막 없이 재시도
            print(f"    자막 합성 실패, 자막 없이 재시도...")
            crop_cmd_no_sub = [
                "ffmpeg", "-y", "-i", raw_path,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                cropped_path
            ]
            run_cmd(crop_cmd_no_sub, f"crop_nosub_short{index:02d}")

        if not os.path.exists(cropped_path):
            print(f"  건너뜀: 크롭 실패")
            return None

        # 4. 인트로 + 본편 + 아웃트로 결합 (concat filter 사용 - 문제 8)
        print(f"  4/4 인트로/아웃트로 결합 중...")
        intro_text = hook if hook else title
        intro_ok = create_text_overlay(intro_text, intro_duration, width, height, intro_path, font_size=52, fps=fps)
        outro_ok = create_text_overlay(outro_text, outro_duration, width, height, outro_path, font_size=44, fps=fps)

        # concat filter 방식 (SAR/샘플레이트 정규화 포함)
        inputs = []
        filter_parts = []
        concat_inputs = []
        input_idx = 0

        if intro_ok and os.path.exists(intro_path):
            inputs.extend(["-i", intro_path])
            filter_parts.append(f"[{input_idx}:v:0]setsar=1[v{input_idx}];[{input_idx}:a:0]aresample=48000[a{input_idx}];")
            concat_inputs.append(f"[v{input_idx}][a{input_idx}]")
            input_idx += 1

        inputs.extend(["-i", cropped_path])
        filter_parts.append(f"[{input_idx}:v:0]setsar=1[v{input_idx}];[{input_idx}:a:0]aresample=48000[a{input_idx}];")
        concat_inputs.append(f"[v{input_idx}][a{input_idx}]")
        input_idx += 1

        if outro_ok and os.path.exists(outro_path):
            inputs.extend(["-i", outro_path])
            filter_parts.append(f"[{input_idx}:v:0]setsar=1[v{input_idx}];[{input_idx}:a:0]aresample=48000[a{input_idx}];")
            concat_inputs.append(f"[v{input_idx}][a{input_idx}]")
            input_idx += 1

        n_segments = len(concat_inputs)
        filter_str = "".join(filter_parts) + "".join(concat_inputs) + f"concat=n={n_segments}:v=1:a=1[outv][outa]"

        concat_cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            final_path
        ]
        result = run_cmd(concat_cmd, f"concat_short{index:02d}")

        # concat filter 실패 시 본편만 사용
        if not os.path.exists(final_path):
            print(f"    결합 실패, 본편만 사용...")
            shutil.copy2(cropped_path, final_path)

        if not os.path.exists(final_path):
            print(f"  건너뜀: 최종 파일 생성 실패")
            return None

        final_size = os.path.getsize(final_path) / 1024 / 1024
        final_duration = get_duration(final_path)
        print(f"  완료: {final_path} ({final_size:.1f}MB, {final_duration:.0f}s)")

        return {
            "index": index,
            "file": f"short_{index:02d}.mp4",
            "title": title,
            "hook": hook,
            "reason": highlight.get("reason", ""),
            "duration": round(final_duration, 1),
            "size_mb": round(final_size, 1),
            "original_start": start,
            "original_end": end,
            "description": f"{hook}\n\n#{title.replace(' ', '')} #쇼츠 #shorts",
            "hashtags": ["#shorts", "#쇼츠", f"#{title.replace(' ', '')}"]
        }


def main():
    parser = argparse.ArgumentParser(description="쇼츠 영상 자동 편집")
    parser.add_argument("--highlights", required=True, help="highlights.json 경로")
    parser.add_argument("--url", required=True, help="원본 YouTube URL")
    parser.add_argument("--output", required=True, help="출력 디렉토리")
    parser.add_argument("--srt", default="", help="전체 SRT 자막 경로")
    parser.add_argument("--config", default="", help="config.yaml 또는 config.json 경로")
    args = parser.parse_args()

    with open(args.highlights, "r", encoding="utf-8") as f:
        highlights = json.load(f)

    os.makedirs(args.output, exist_ok=True)
    os.makedirs("output/logs", exist_ok=True)

    srt_path = args.srt
    if not srt_path:
        srt_candidate = os.path.join(os.path.dirname(args.highlights), "transcript.srt")
        if os.path.exists(srt_candidate):
            srt_path = srt_candidate

    config = {
        "width": 1080, "height": 1920,
        "intro_duration": 2, "outro_duration": 2,
        "outro_text": "구독과 좋아요 부탁드립니다!",
        "subtitle_font_size": 28, "subtitle_font_color": "white",
        "subtitle_border_width": 2,
    }

    if args.config and os.path.exists(args.config):
        try:
            import yaml
            with open(args.config, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
            if user_config:
                config.update(user_config)
        except ImportError:
            try:
                with open(args.config, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                config.update(user_config)
            except Exception:
                pass

    print(f"=== 쇼츠 영상 생성 ===")
    print(f"하이라이트: {len(highlights)}개")
    print(f"출력: {args.output}")
    print(f"해상도: {config['width']}x{config['height']}")
    print(f"컨테이너: {'예' if is_container_env() else '아니오'}")
    font = get_font_path()
    print(f"한글 폰트: {font or '없음 (시스템 기본)'}")
    print()

    results = []
    failures = []
    for highlight in highlights:
        idx = highlight.get("index", len(results) + 1)
        result = process_short(idx, highlight, args.url, args.output, srt_path, config)
        if result:
            results.append(result)
        else:
            failures.append({"index": idx, "title": highlight.get("title", ""), "reason": "처리 실패"})

    metadata_path = os.path.join(args.output, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"shorts": results, "failures": failures}, f, ensure_ascii=False, indent=2)

    total_size = sum(r["size_mb"] for r in results)
    total_duration = sum(r["duration"] for r in results)

    print(f"\n=== 생성 완료 ===")
    print(f"성공: {len(results)}/{len(highlights)}개")
    if failures:
        print(f"실패: {len(failures)}개")
        for f_item in failures:
            print(f"  [{f_item['index']:02d}] {f_item['title']} - {f_item['reason']}")
    print(f"총 용량: {total_size:.1f}MB")
    print(f"총 길이: {total_duration:.0f}초")
    print(f"메타데이터: {metadata_path}")
    if failures:
        print(f"에러 로그: output/logs/")

    for r in results:
        print(f"  [{r['index']:02d}] {r['title']} - {r['duration']:.0f}s ({r['size_mb']:.1f}MB)")


if __name__ == "__main__":
    main()
