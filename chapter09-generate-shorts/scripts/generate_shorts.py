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


def _filter_path(p: str) -> str:
    """ffmpeg 필터 옵션 값(작은따옴표로 감싼 경로)용 이스케이프.
    콜론은 백슬래시로 이스케이프하고, 작은따옴표는 따옴표를 닫고 \\'를 넣은 뒤
    다시 여는 방식('\\'')을 쓴다 — 따옴표 안에서는 백슬래시 이스케이프가 동작하지 않기 때문."""
    p = p.replace("\\", "/").replace(":", "\\:")
    return p.replace("'", "'\\''")


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


def has_audio_stream(video_path: str) -> bool:
    """영상에 오디오 스트림이 있는지 확인 (concat 조립 전 필수 체크)"""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def get_duration(video_path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except (ValueError, OSError):
        # ffprobe 부재(FileNotFoundError 포함)나 출력 이상도 0으로 처리해 전체 실행을 살린다
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

        # 파일 존재 확인 (정확한 경로) + 유효성 검증
        # (손상/부분 파일이 영구 캐시로 승격되면 이후 모든 인코딩이 반복 실패한다)
        if os.path.exists(output_path):
            if get_duration(output_path) > 0:
                random_delay()
                return True
            os.remove(output_path)

        # yt-dlp가 다른 이름으로 저장했을 수 있음 (문제 6)
        # 단 .part/.ytdl 같은 미완성 임시 파일은 절대 승격하지 않는다
        base = os.path.splitext(output_path)[0]
        candidates = [c for c in glob.glob(f"{base}*")
                      if not c.endswith((".part", ".ytdl", ".temp"))]
        if candidates:
            os.rename(candidates[0], output_path)
            if get_duration(output_path) > 0:
                random_delay()
                return True
            os.remove(output_path)

        if result.returncode != 0:
            stderr_lower = result.stderr.lower()
            if "sign in" in stderr_lower or "bot" in stderr_lower:
                print(f"    봇 감지 - 쿠키 확인 필요")

    return False


def _video_id(url: str) -> str:
    """캐시 키용 영상 식별자. 같은 캐시 디렉토리를 다른 영상이 공유할 때
    이전 영상의 구간을 재사용하는 사고를 막는다."""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{6,})", url or "")
    if m:
        return m.group(1)[:16]
    fallback = re.sub(r"[^A-Za-z0-9_-]", "", url or "")
    return (fallback[-12:] or "local")


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


# --- 자막(ASS) 생성 ---

def _sec_to_ass(t: float) -> str:
    """초(float) -> ASS 시간(0:01:02.34)"""
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = min(int(round((t - int(t)) * 100)), 99)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(
    events: list, ass_path: str, font_name: str, font_size: int,
    width: int, height: int, margin_v: int, outline: int
) -> int:
    """자막 이벤트 [(시작초, 끝초, 텍스트), ...] 를 ASS 자막 파일로 쓴다.

    핵심: ffmpeg의 subtitles(SRT) 필터는 PlayRes를 기본 384x288로 잡아서
    FontSize를 최종 프레임(1080x1920)에 맞춰 6배 이상 확대해 버린다(자막이 화면을 덮음).
    ASS를 직접 만들어 PlayResX/Y를 실제 해상도로 지정하면 FontSize가 실제 픽셀이 되어
    자막 크기가 환경과 무관하게 예측 가능해진다.
    이벤트 시간은 영상 시작 기준 상대 초. 반환: 기록된 이벤트 수.
    """
    valid = []
    for start, end, text in events:
        # ASS 오버라이드 블록으로 오인되지 않도록 중괄호 치환
        text = str(text).replace("{", "(").replace("}", ")").replace("\r", "").strip()
        # 리터럴 개행은 ASS 줄바꿈(\N)으로 — 그대로 두면 Dialogue 줄이 쪼개져 뒷줄이 조용히 사라진다
        text = text.replace("\n", "\\N")
        try:
            start_f, end_f = float(start), float(end)
        except (TypeError, ValueError):
            continue
        if text and end_f > start_f:
            valid.append((start_f, end_f, text))

    fn = font_name or "Sans"
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 0\n"  # 0 = 긴 줄 자동 줄바꿈(좌우 여백 안에서). 2는 자동 줄바꿈이 없어 화면 밖으로 넘친다.
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{fn},{font_size},&H00FFFFFF,&H00000000,&H64000000,"
        f"0,0,0,0,100,100,0,0,3,{outline},0,2,60,60,{margin_v},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header)
        for start, end, text in valid:
            f.write(f"Dialogue: 0,{_sec_to_ass(start)},{_sec_to_ass(end)},Default,,0,0,0,,{text}\n")
    return len(valid)


def write_ass_from_srt(
    srt_path: str, ass_path: str, font_name: str, font_size: int,
    width: int, height: int, margin_v: int, outline: int
) -> int:
    """구간 SRT를 ASS로 변환한다 (Claude 재구성 자막이 없을 때의 폴백)."""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    events = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        start_str, end_str = lines[1].split(" --> ")
        text = "\\N".join(ln.strip() for ln in lines[2:] if ln.strip())
        if text:
            events.append((_parse_srt_time(start_str.strip()), _parse_srt_time(end_str.strip()), text))

    return write_ass(events, ass_path, font_name, font_size, width, height, margin_v, outline)


# --- 텍스트 오버레이 (인트로/아웃트로) ---

def wrap_text(text: str, max_chars: int = 11, max_lines: int = 4) -> str:
    """인트로/아웃트로 카드 텍스트를 줄바꿈한다.
    drawtext는 자동 줄바꿈이 없어, 긴 문장을 그대로 넣으면 한 줄로 화면 밖까지 넘친다.
    """
    text = (text or "").strip()
    if not text:
        return ""
    lines, cur = [], ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if len(cand) <= max_chars:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        # 한 단어가 너무 길면 강제로 자른다
        while len(word) > max_chars:
            lines.append(word[:max_chars])
            word = word[max_chars:]
        cur = word
    if cur:
        lines.append(cur)
    return "\n".join(lines[:max_lines])


def create_text_overlay(
    text: str, duration: float, width: int, height: int,
    output_path: str, font_size: int = 48, fps: float = 30,
    bg_color: str = "black"
):
    """텍스트 오버레이 영상 (한글 폰트 지정, 자동 줄바꿈, fps 맞춤).
    텍스트는 textfile로 전달해 따옴표/콜론 이스케이프 문제를 피하고, 여러 줄을 지원한다.
    """
    font_path = get_font_path()
    fontfile_opt = f":fontfile='{_filter_path(font_path)}'" if font_path else ""

    txt_file = output_path + ".txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(wrap_text(text))

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={width}x{height}:d={duration}:r={fps}",
        "-f", "lavfi",
        "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(duration),
        "-vf", (
            f"drawtext=textfile='{_filter_path(txt_file)}':"
            f"fontsize={font_size}:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            # expansion=none: 텍스트에 %가 있으면 기본 expansion이 렌더링을 통째로 삼킨다
            f"line_spacing=18:borderw=4:bordercolor=black:expansion=none"
            f"{fontfile_opt}"
        ),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    result = run_cmd(cmd, f"overlay_{os.path.basename(output_path)}")
    return result is not None and result.returncode == 0


# --- 후크 오버레이 ---

def build_hook_drawtext(hook_txt_path: str, font_path, font_size: int, duration: float) -> str:
    """본편 첫 부분 위에 얹는 후크 텍스트 필터를 만든다.

    검은 인트로 카드 대신 쓰는 이유: 쇼츠의 첫 1~2초가 정지된 검은 화면이면
    시청자가 내용을 보기도 전에 스와이프한다. 본편을 즉시 보여주면서 그 위에
    후크 문구를 얹어야 이탈 없이 관심을 끌 수 있다.
    """
    fontfile_opt = f":fontfile='{_filter_path(font_path)}'" if font_path else ""
    return (
        f"drawtext=textfile='{_filter_path(hook_txt_path)}':"
        f"fontsize={font_size}:fontcolor=white:"
        f"x=(w-text_w)/2:y=h*0.14:"
        f"line_spacing=14:"
        f"box=1:boxcolor=black@0.45:boxborderw=22:"
        # expansion=none: 텍스트에 %가 있으면 기본 expansion이 렌더링을 통째로 삼킨다
        f"expansion=none:"
        f"enable='between(t,0,{duration})'"
        f"{fontfile_opt}"
    )


# --- 세로 레이아웃 (16:9 -> 9:16 변환) ---

def build_layout_filtergraph(
    layout: str, width: int, height: int,
    blur_radius: int, post_filters: str
) -> str:
    """
    원본을 세로(width x height)로 변환하는 filter_complex 문자열을 만든다.
    반환 그래프는 [0:v]를 입력으로 받아 [outv]를 출력한다.

    핵심: 원본이 16:9 가로 영상일 때 세로로 바꾸는 방식이 결과 품질을 좌우한다.
    화면 녹화/코드/슬라이드처럼 가장자리 정보가 중요한 영상을 crop으로 처리하면
    좌우가 잘려 글자를 못 읽게 된다. 그래서 기본값은 잘라내지 않는 fit_blur이다.

    layout:
      - "fit_blur" (기본): 원본 전체를 폭에 맞춰 넣고 위아래 여백을 같은 화면의
        블러 확대본으로 채운다. 화면 어디도 잘리지 않아 화면 녹화/코드/슬라이드/
        강의/게임 등 가장자리 정보가 중요한 영상에 안전하다. ("auto"도 여기로.)
      - "fit": 블러 없이 단색(검정) 레터박스. 배경을 깔끔하게 두고 싶을 때.
      - "crop": 가운데를 꽉 채우고 좌우를 잘라낸다. 인물이 화면 중앙에 있는
        토킹헤드/인터뷰/브이로그처럼 "가운데만 중요한" 영상에만 적합하다.

    post_filters: 레이아웃 뒤에 이어붙일 필터 체인(자막 ass=..., 후크 drawtext=... 등,
                  콤마로 연결, 앞 콤마 없이). 없으면 빈 문자열.
    """
    sub = f",{post_filters}" if post_filters else ""

    if layout == "crop":
        return (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}{sub}[outv]"
        )
    if layout == "fit":
        return (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black{sub}[outv]"
        )
    # fit_blur (기본값, "auto" 포함): 잘라내지 않는 안전한 방식
    return (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},boxblur={blur_radius}:1[bgb];"
        f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2{sub}[outv]"
    )


def make_hashtag(text: str) -> str:
    """제목에서 안전한 해시태그를 만든다 (특수문자/공백 제거)."""
    tag = re.sub(r"[^0-9A-Za-z가-힣]", "", text or "")[:20]
    return f"#{tag}" if tag else ""


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

    cache_dir = config.get("cache_dir", "")
    # 캐시 키 = 영상ID + 번호 + 구간 경계.
    # 경계가 빠지면 highlights 수정 후 stale 구간을 재사용하고,
    # 영상ID가 빠지면 다른 영상의 구간을 재사용하는 사고가 난다.
    cached = (os.path.join(cache_dir, f"seg_{_video_id(url)}_{index:02d}_{start:.1f}-{end:.1f}.mp4")
              if cache_dir else None)

    width = config.get("width", 1080)
    height = config.get("height", 1920)
    intro_duration = config.get("intro_duration", 2)
    outro_duration = config.get("outro_duration", 2)
    outro_text = config.get("outro_text", "구독과 좋아요 부탁드립니다!")
    font_size = config.get("subtitle_font_size", 54)
    border_width = config.get("subtitle_border_width", 3)
    subtitle_margin_v = config.get("subtitle_margin_v", 150)
    layout = config.get("layout", "fit_blur")
    blur_radius = config.get("bg_blur_radius", 20)
    hook_overlay = bool(config.get("hook_overlay", True))
    hook_duration = float(config.get("hook_duration", 2.5))
    hook_font_size = int(config.get("hook_font_size", 64))
    use_intro_card = bool(config.get("intro_card", False))
    use_outro = bool(config.get("outro_enabled", False))

    font_path = get_font_path()

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = os.path.join(tmpdir, f"raw_{index:02d}.mp4")
        # SRT를 심플한 이름으로 (문제 9: 특수문자 방지)
        section_srt = os.path.join(tmpdir, f"sub.srt")
        cropped_path = os.path.join(tmpdir, f"cropped.mp4")
        intro_path = os.path.join(tmpdir, f"intro.mp4")
        outro_path = os.path.join(tmpdir, f"outro.mp4")
        final_path = os.path.join(output_dir, f"short_{index:02d}.mp4")

        # 1. 구간 확보 — 캐시 우선 (재실행/시간 제한 환경에서 재다운로드 방지)
        if cached and os.path.exists(cached) and os.path.getsize(cached) > 0 and get_duration(cached) > 0:
            print(f"  1/4 캐시된 구간 사용 ({os.path.basename(cached)})...")
            shutil.copy2(cached, raw_path)
        else:
            print(f"  1/4 구간 다운로드 중...")
            if not download_section(url, start, end, raw_path):
                print(f"  건너뜀: 다운로드 실패")
                return None
            if cached:
                os.makedirs(cache_dir, exist_ok=True)
                shutil.copy2(raw_path, cached)

        # 본편 영상 정보 추출 (문제 8: fps 맞춤)
        video_info = get_video_info(raw_path)
        fps = video_info["fps"]

        # 2. 자막 준비 — Claude가 재구성한 자막(highlights.json의 subtitles)이 있으면 우선 사용
        print(f"  2/4 자막 준비 중...")
        font_name = ""
        if font_path:
            font_name = os.path.basename(font_path).replace(".ttc", "").replace(".ttf", "")
        ass_path = os.path.join(tmpdir, "sub.ass")
        n_events = 0
        curated_subs = highlight.get("subtitles")
        if curated_subs:
            events = []
            for s in curated_subs:
                try:
                    events.append((float(s["start"]), float(s["end"]), str(s["text"])))
                except (KeyError, TypeError, ValueError):
                    continue
            n_events = write_ass(events, ass_path, font_name, font_size,
                                 width, height, subtitle_margin_v, border_width)
            print(f"    재구성 자막 {n_events}개 사용 (Claude 큐레이션)")
        elif curated_subs is not None:
            # 명시적 빈 배열([]) = 자막을 의도적으로 생략 (원본에 자막이 구워진 영상 등)
            print(f"    자막 생략 (subtitles: [])")
        else:
            # 필드 없음 → 폴백: 원본 자동자막을 구간만 잘라 사용 (롤링 파편 그대로라 품질 낮음)
            extract_srt_for_section(srt_path, start, end, section_srt)
            if os.path.exists(section_srt) and os.path.getsize(section_srt) > 0:
                n_events = write_ass_from_srt(section_srt, ass_path, font_name, font_size,
                                              width, height, subtitle_margin_v, border_width)

        # 3. 세로 레이아웃 + 자막 + 후크 오버레이
        print(f"  3/4 세로 레이아웃({layout}) + 자막/후크 합성 중...")
        post_parts = []
        if n_events > 0:
            post_parts.append(f"ass='{_filter_path(ass_path)}'")

        hook_text = (hook or title or "").strip()
        if hook_overlay and hook_text:
            hook_txt_path = os.path.join(tmpdir, "hook.txt")
            with open(hook_txt_path, "w", encoding="utf-8") as f:
                f.write(wrap_text(hook_text, max_chars=12, max_lines=3))
            post_parts.append(build_hook_drawtext(hook_txt_path, font_path, hook_font_size, hook_duration))

        def _run_layout(post: str, tag: str):
            filtergraph = build_layout_filtergraph(layout, width, height, blur_radius, post)
            cmd = [
                "ffmpeg", "-y", "-i", raw_path,
                "-filter_complex", filtergraph,
                "-map", "[outv]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                cropped_path
            ]
            return run_cmd(cmd, tag)

        result = _run_layout(",".join(post_parts), f"layout_short{index:02d}")

        if result is None or result.returncode != 0:
            # 자막/후크 합성 실패 시 레이아웃만으로 재시도
            print(f"    자막/후크 합성 실패, 오버레이 없이 재시도...")
            retry = _run_layout("", f"layout_nosub_short{index:02d}")
            if retry is None or retry.returncode != 0:
                # ffmpeg -y는 실패해도 부분 파일을 남기므로, 지워서 성공으로 오인되지 않게 한다
                if os.path.exists(cropped_path):
                    os.remove(cropped_path)

        if not os.path.exists(cropped_path):
            print(f"  건너뜀: 크롭 실패")
            return None

        # 4. (옵션) 인트로/아웃트로 카드 — 기본 꺼짐.
        # 검은 정지 카드가 앞에 붙으면 첫 1초에 시청자가 이탈하므로,
        # 기본값은 카드 없이 본편 위 후크 오버레이만 쓴다 (3단계에서 이미 합성됨).
        intro_ok = False
        outro_ok = False
        if use_intro_card:
            intro_text = title if title else hook
            intro_ok = create_text_overlay(intro_text, intro_duration, width, height, intro_path, font_size=64, fps=fps)
        if use_outro:
            outro_ok = create_text_overlay(outro_text, outro_duration, width, height, outro_path, font_size=56, fps=fps)

        if not intro_ok and not outro_ok:
            # 카드 없음(기본): 본편이 곧 최종본 (재인코딩 생략)
            print(f"  4/4 마무리 중...")
            shutil.copy2(cropped_path, final_path)
        else:
            print(f"  4/4 인트로/아웃트로 결합 중...")
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
            if has_audio_stream(cropped_path):
                filter_parts.append(f"[{input_idx}:v:0]setsar=1[v{input_idx}];[{input_idx}:a:0]aresample=48000[a{input_idx}];")
                concat_inputs.append(f"[v{input_idx}][a{input_idx}]")
                input_idx += 1
            else:
                # 원본에 오디오가 없으면 [N:a:0] 참조가 concat 전체를 실패시키므로 무음 트랙을 주입한다
                vid_idx = input_idx
                aud_idx = input_idx + 1
                main_dur = get_duration(cropped_path) or (end - start)
                inputs.extend(["-f", "lavfi", "-t", f"{main_dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"])
                filter_parts.append(f"[{vid_idx}:v:0]setsar=1[v{vid_idx}];[{aud_idx}:a:0]aresample=48000[a{vid_idx}];")
                concat_inputs.append(f"[v{vid_idx}][a{vid_idx}]")
                input_idx += 2

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

            # concat 실패 시 본편만 사용.
            # 주의: ffmpeg -y는 실패해도 0바이트 출력을 남기므로 존재 여부만으로 판정하면 안 된다.
            concat_failed = (result is None or result.returncode != 0)
            if concat_failed or not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                print(f"    결합 실패, 본편만 사용...")
                if os.path.exists(final_path):
                    os.remove(final_path)
                shutil.copy2(cropped_path, final_path)

        if not os.path.exists(final_path):
            print(f"  건너뜀: 최종 파일 생성 실패")
            return None

        final_size = os.path.getsize(final_path) / 1024 / 1024
        final_duration = get_duration(final_path)
        print(f"  완료: {final_path} ({final_size:.1f}MB, {final_duration:.0f}s)")

        topic_tag = make_hashtag(title)
        hashtags = ["#shorts", "#쇼츠"] + ([topic_tag] if topic_tag else [])

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
            "description": f"{hook}\n\n{' '.join(hashtags)}",
            "hashtags": hashtags,
        }


def main():
    parser = argparse.ArgumentParser(description="쇼츠 영상 자동 편집")
    parser.add_argument("--highlights", required=True, help="highlights.json 경로")
    parser.add_argument("--url", required=True, help="원본 YouTube URL")
    parser.add_argument("--output", required=True, help="출력 디렉토리")
    parser.add_argument("--srt", default="", help="전체 SRT 자막 경로")
    parser.add_argument("--config", default="", help="config.yaml 또는 config.json 경로")
    parser.add_argument(
        "--layout", default="",
        help="세로 변환 방식: fit_blur(기본, 잘림 없음)|crop(가운데만, 좌우 잘림)|fit(단색 레터박스)"
    )
    parser.add_argument(
        "--only", default="",
        help="지정한 번호의 쇼츠만 처리 (예: 2 또는 2,3) — 명령 시간 제한이 있는 환경(코워크)용"
    )
    parser.add_argument(
        "--download-only", action="store_true",
        help="하이라이트 구간을 캐시에 다운로드만 하고 종료 (다운로드/인코딩 분리 실행용)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="이미 완성된 쇼츠도 다시 생성 (기본은 건너뜀)"
    )
    args = parser.parse_args()

    with open(args.highlights, "r", encoding="utf-8") as f:
        highlights = json.load(f)

    # 하이라이트 정규화 — 다운로드/인코딩 두 경로가 같은 규칙을 쓰도록 한 곳에서 처리.
    # (타입 오류 항목 하나가 배치 전체를 죽이거나, index 기본값이 경로마다 달라
    #  캐시 키가 어긋나는 문제를 막는다)
    normalized = []
    for pos, h in enumerate(highlights, 1):
        if not isinstance(h, dict):
            print(f"경고: 하이라이트 {pos}번이 객체가 아님 — 건너뜀")
            continue
        try:
            h["start"] = float(h["start"])
            h["end"] = float(h["end"])
        except (KeyError, TypeError, ValueError):
            print(f"경고: 하이라이트 {pos}번 start/end 형식 오류 — 건너뜀")
            continue
        if h["end"] <= h["start"]:
            print(f"경고: 하이라이트 {pos}번 구간 오류 (start >= end) — 건너뜀")
            continue
        try:
            h["index"] = int(h.get("index", pos))
        except (TypeError, ValueError):
            h["index"] = pos
        normalized.append(h)
    if not normalized:
        print("ERROR: 유효한 하이라이트가 없습니다.")
        sys.exit(1)
    highlights = normalized

    os.makedirs(args.output, exist_ok=True)
    os.makedirs("output/logs", exist_ok=True)

    srt_path = args.srt
    if not srt_path:
        srt_candidate = os.path.join(os.path.dirname(args.highlights), "transcript.srt")
        if os.path.exists(srt_candidate):
            srt_path = srt_candidate

    config = {
        "width": 1080, "height": 1920,
        "hook_overlay": True, "hook_duration": 2.5, "hook_font_size": 64,
        "intro_card": False, "outro_enabled": False,
        "intro_duration": 2, "outro_duration": 2,
        "outro_text": "구독과 좋아요 부탁드립니다!",
        "subtitle_font_size": 54,
        "subtitle_border_width": 3, "subtitle_margin_v": 150,
        "layout": "fit_blur", "bg_blur_radius": 20,
    }

    if args.config and os.path.exists(args.config):
        user_config = None
        try:
            import yaml
            with open(args.config, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
        except ImportError:
            # PyYAML이 없으면 JSON으로 시도
            try:
                with open(args.config, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
            except Exception:
                print(f"경고: config 파싱 실패 (JSON 아님, PyYAML 미설치) — 기본값 사용: {args.config}")
        except Exception as e:
            print(f"경고: config 파싱 실패 — 기본값 사용: {e}")
        if isinstance(user_config, dict):
            config.update(user_config)
        elif user_config is not None:
            print(f"경고: config 최상위가 매핑(dict)이 아님 — 무시: {args.config}")

    # CLI --layout 은 config 파일보다 우선한다
    if args.layout:
        config["layout"] = args.layout

    # 구간 캐시: output/shorts -> output/cache (재실행 시 재다운로드 방지).
    # --output이 "." 처럼 cwd 이상을 가리키면 부모가 작업 트리 밖이 되므로 output 내부로 고정
    out_abs = os.path.abspath(args.output)
    cwd_abs = os.path.abspath(os.getcwd())
    if out_abs == cwd_abs or cwd_abs.startswith(out_abs + os.sep):
        cache_dir = os.path.join(out_abs, "cache")
    else:
        cache_dir = os.path.join(os.path.dirname(out_abs), "cache")
    config["cache_dir"] = cache_dir

    only = set()
    if args.only:
        try:
            only = {int(x) for x in args.only.split(",") if x.strip()}
        except ValueError:
            print(f"ERROR: --only 형식 오류 (예: 2 또는 2,3): {args.only}")
            sys.exit(1)
        if not only:
            print(f"ERROR: --only에 유효한 번호가 없습니다: {args.only!r}")
            sys.exit(1)
        valid_idx = {h["index"] for h in highlights}
        if not (only & valid_idx):
            print(f"ERROR: --only {sorted(only)} 는 하이라이트에 없습니다 (있는 번호: {sorted(valid_idx)})")
            sys.exit(1)
        unknown = only - valid_idx
        if unknown:
            print(f"경고: --only 중 {sorted(unknown)} 는 하이라이트에 없어 무시됩니다")

    # 다운로드 전용 모드: 구간만 캐시에 받고 종료 (코워크처럼 명령당 시간 제한이 있는 환경에서
    # 다운로드(~20초)와 인코딩(~25초)을 별도 명령으로 나누기 위한 모드)
    if args.download_only:
        os.makedirs(cache_dir, exist_ok=True)
        print(f"=== 구간 다운로드 전용 모드 (캐시: {cache_dir}) ===")
        ok = 0
        vid = _video_id(args.url)
        for highlight in highlights:
            idx = highlight["index"]
            if only and idx not in only:
                continue
            start, end = highlight["start"], highlight["end"]
            cached = os.path.join(cache_dir, f"seg_{vid}_{idx:02d}_{start:.1f}-{end:.1f}.mp4")
            if os.path.exists(cached) and os.path.getsize(cached) > 0 and get_duration(cached) > 0:
                print(f"[{idx:02d}] 이미 캐시됨 — 건너뜀")
                ok += 1
                continue
            print(f"[{idx:02d}] {start:.1f}s-{end:.1f}s 다운로드...")
            if download_section(args.url, start, end, cached):
                ok += 1
            else:
                print(f"[{idx:02d}] 다운로드 실패")
        print(f"완료: {ok}개 캐시됨. 이제 --only N 으로 하나씩 인코딩하세요.")
        return

    print(f"=== 쇼츠 영상 생성 ===")
    print(f"하이라이트: {len(highlights)}개")
    print(f"출력: {args.output}")
    print(f"해상도: {config['width']}x{config['height']}")
    print(f"레이아웃: {config.get('layout', 'fit_blur')}")
    print(f"컨테이너: {'예' if is_container_env() else '아니오'}")
    font = get_font_path()
    print(f"한글 폰트: {font or '없음 (시스템 기본)'}")
    print()

    results = []
    failures = []
    for highlight in highlights:
        idx = highlight["index"]
        if only and idx not in only:
            continue

        # 재실행 안전: 이미 완성된 쇼츠는 건너뛴다 (시간 제한 환경에서 이어서 실행 가능).
        # duration 검증까지 해서 손상/부분 파일이 성공으로 오인되지 않게 한다
        final_path = os.path.join(args.output, f"short_{idx:02d}.mp4")
        if not args.force and os.path.exists(final_path) and os.path.getsize(final_path) > 0 \
                and get_duration(final_path) > 0:
            size_mb = os.path.getsize(final_path) / 1024 / 1024
            print(f"\n--- Short {idx:02d}: 이미 존재 — 건너뜀 (다시 만들려면 --force) ---")
            title = highlight.get("title", f"Short {idx}")
            hook = highlight.get("hook", "")
            topic_tag = make_hashtag(title)
            hashtags = ["#shorts", "#쇼츠"] + ([topic_tag] if topic_tag else [])
            results.append({
                "index": idx,
                "file": f"short_{idx:02d}.mp4",
                "title": title,
                "hook": hook,
                "reason": highlight.get("reason", ""),
                "duration": round(get_duration(final_path), 1),
                "size_mb": round(size_mb, 1),
                "original_start": highlight.get("start"),
                "original_end": highlight.get("end"),
                "description": f"{hook}\n\n{' '.join(hashtags)}",
                "hashtags": hashtags,
            })
            continue

        result = process_short(idx, highlight, args.url, args.output, srt_path, config)
        if result:
            results.append(result)
        else:
            failures.append({"index": idx, "title": highlight.get("title", ""), "reason": "처리 실패"})

    run_success = len(results)
    run_fail = len(failures)

    metadata_path = os.path.join(args.output, "metadata.json")
    # --only 실행 시 기존 metadata와 병합 (부분 실행이 전체 목록을 지우지 않도록).
    # 이번 실행에서 성공한 index는 기존 failures에서 빼고, 실패한 index는 기존 shorts에서 뺀다.
    if only and os.path.exists(metadata_path):
        merged, old_fail = {}, {}
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            merged = {s.get("index"): s for s in old.get("shorts", []) if s.get("index") is not None}
            old_fail = {x.get("index"): x for x in old.get("failures", []) if x.get("index") is not None}
        except Exception as e:
            print(f"경고: 기존 metadata.json 파싱 실패 — 이번 실행 결과만 기록합니다 ({e})")
        for r in results:
            merged[r["index"]] = r
            old_fail.pop(r["index"], None)
        for x in failures:
            old_fail[x["index"]] = x
            merged.pop(x["index"], None)
        results = [merged[k] for k in sorted(merged)]
        failures = [old_fail[k] for k in sorted(old_fail)]
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"shorts": results, "failures": failures}, f, ensure_ascii=False, indent=2)

    total_size = sum(r["size_mb"] for r in results)
    total_duration = sum(r["duration"] for r in results)

    print(f"\n=== 생성 완료 ===")
    scope = f" (--only {sorted(only)})" if only else ""
    print(f"이번 실행: 성공 {run_success}개 / 실패 {run_fail}개{scope}")
    print(f"전체 목록: 쇼츠 {len(results)}개")
    if failures:
        print(f"실패 목록: {len(failures)}개")
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
