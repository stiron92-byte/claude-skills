#!/usr/bin/env python3
"""
YouTube 자체 자막 추출
- 수동자막 우선, 없으면 자동생성 자막 사용
- 컨테이너 환경 자동 감지 (--cookies-from-browser 조건부)
- 에러 발생 시 output/logs/에 상세 로그 저장
"""

import argparse
import json
import os
import platform
import random
import re
import subprocess
import sys
import time


# --- 봇 감지 우회 설정 ---

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
    """claude.ai 컨테이너 환경 감지"""
    if os.environ.get("CLAUDE_CONTAINER") == "1":
        return True
    if os.path.isdir("/home/claude"):
        return True
    if os.path.exists("/.dockerenv"):
        return True
    return False


def get_cookie_browser() -> str | None:
    """쿠키 브라우저 결정 (컨테이너면 None)"""
    if is_container_env():
        return None
    return os.environ.get("YT_COOKIE_BROWSER", "chrome")


def get_cookie_file() -> str | None:
    """cookies.txt 파일 탐색"""
    candidates = ["cookies.txt", "output/cookies.txt", os.path.expanduser("~/cookies.txt")]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def get_proxy() -> str | None:
    return os.environ.get("YT_PROXY")


def random_delay():
    time.sleep(random.uniform(BASE_DELAY, MAX_DELAY))


def log_error(description: str, cmd: list, result) -> str:
    """에러 로그를 output/logs/에 저장하고 경로 반환"""
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


def build_ytdlp_base_args(use_cookies: bool = False) -> list:
    """yt-dlp 공통 인자. use_cookies=True는 봇 감지 실패 시 재시도용"""
    args = [
        "yt-dlp",
        "--user-agent", get_user_agent(),
    ]

    # 쿠키: 명시적으로 요청된 경우에만 추가 (키체인 팝업 방지)
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


def extract_subtitles(url: str, output_dir: str, lang: str = "ko") -> str | None:
    """YouTube 자막 추출 (수동 -> 자동 -> 아무 언어)"""
    os.makedirs(output_dir, exist_ok=True)

    # 1차: 수동 자막
    print(f"[1/3] 수동 자막 추출 시도 (lang={lang})...")
    srt_path = _try_download_subs(url, output_dir, lang, auto=False)
    if srt_path:
        print(f"  수동 자막 발견: {srt_path}")
        return srt_path

    # 2차: 자동생성 자막
    print(f"[2/3] 자동생성 자막 추출 시도...")
    srt_path = _try_download_subs(url, output_dir, lang, auto=True)
    if srt_path:
        print(f"  자동 자막 발견: {srt_path}")
        return srt_path

    # 3차: 아무 언어
    print(f"[3/3] 사용 가능한 자막 탐색...")
    srt_path = _try_any_language(url, output_dir)
    if srt_path:
        print(f"  대체 자막 발견: {srt_path}")
    else:
        print("  자막을 찾을 수 없습니다.")

    return srt_path


def _try_download_subs(url: str, output_dir: str, lang: str, auto: bool) -> str | None:
    """자막 다운로드: 쿠키 없이 먼저 시도 -> 실패 시 쿠키 재시도"""
    prefix = "auto_sub" if auto else "manual_sub"

    # 1차: 쿠키 없이 시도 (키체인 팝업 방지)
    for attempt in range(2):
        use_cookies = attempt > 0  # 두 번째부터 쿠키 사용
        if attempt > 0:
            backoff = BASE_DELAY * 2 + random.uniform(0, 2)
            print(f"  쿠키 포함 재시도 ({backoff:.0f}초 대기)...")
            time.sleep(backoff)

        try:
            output_template = os.path.join(output_dir, prefix)
            cmd = build_ytdlp_base_args(use_cookies=use_cookies)
            if auto:
                cmd.extend(["--write-auto-sub", "--sub-lang", lang])
            else:
                cmd.extend(["--write-sub", "--sub-lang", lang])
            cmd.extend([
                "--skip-download",
                "--convert-subs", "srt",
                "-o", output_template,
                url,
            ])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # SRT 파일 확인 (returncode와 무관하게 파일 생성됐을 수 있음)
            srt_path = _find_srt(output_dir, prefix)
            if srt_path:
                return srt_path

            if result.returncode != 0:
                log_path = log_error(f"subtitle_{prefix}_attempt{attempt}", cmd, result)
                stderr = result.stderr.lower()
                is_bot_blocked = any(kw in stderr for kw in ["sign in", "bot", "po token", "confirm"])
                if is_bot_blocked and not use_cookies:
                    print(f"  봇 감지 - 쿠키 재시도 예정")
                    continue  # 쿠키 포함 재시도
                elif is_bot_blocked:
                    print(f"  봇 감지 (쿠키 포함) - cookies.txt 확인 필요")

        except subprocess.TimeoutExpired:
            print(f"  타임아웃 (시도 {attempt + 1})")
        except Exception as e:
            print(f"  오류: {e}")

    return None


def _try_any_language(url: str, output_dir: str) -> str | None:
    """사용 가능한 아무 자막이나 추출"""
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            time.sleep(BASE_DELAY * (2 ** attempt))

        try:
            cmd = build_ytdlp_base_args(use_cookies=attempt > 0) + [
                "--list-subs", "--skip-download", url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                log_error(f"list_subs_attempt{attempt}", cmd, result)
                continue

            available_langs = _parse_available_langs(result.stdout)
            if not available_langs:
                return None

            target_lang = None
            for preferred in ["ko", "en"]:
                if preferred in available_langs:
                    target_lang = preferred
                    break
            if not target_lang:
                target_lang = available_langs[0]

            print(f"  사용 가능: {', '.join(available_langs[:5])}... -> {target_lang} 선택")
            random_delay()

            output_template = os.path.join(output_dir, "any_sub")
            cmd = build_ytdlp_base_args(use_cookies=attempt > 0) + [
                "--write-auto-sub", "--write-sub",
                "--sub-lang", target_lang,
                "--skip-download", "--convert-subs", "srt",
                "-o", output_template, url,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            srt_path = _find_srt(output_dir, "any_sub")
            if srt_path:
                return srt_path

        except Exception as e:
            print(f"  오류: {e}")

    return None


def _find_srt(directory: str, prefix: str) -> str | None:
    for f in os.listdir(directory):
        if f.startswith(prefix) and f.endswith(".srt"):
            return os.path.join(directory, f)
    return None


def _parse_available_langs(stdout: str) -> list:
    langs = []
    in_table = False
    for line in stdout.split("\n"):
        line = line.strip()
        if "Language" in line and ("Name" in line or "Formats" in line):
            in_table = True
            continue
        if in_table and line:
            parts = line.split()
            if parts and re.match(r'^[a-z]{2}(-[a-zA-Z]+)?$', parts[0]):
                langs.append(parts[0])
    return langs


def parse_srt_to_transcript(srt_path: str) -> dict:
    """SRT -> transcript JSON (중복 제거, HTML 태그 제거)"""
    chunks = []
    full_text = []

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    prev_text = ""

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        time_line = lines[1]
        text = " ".join(lines[2:]).strip()
        text = re.sub(r'<[^>]+>', '', text).strip()

        if not text or text == prev_text:
            continue
        if " --> " not in time_line:
            continue

        start_str, end_str = time_line.split(" --> ")
        start = _parse_srt_time(start_str.strip())
        end = _parse_srt_time(end_str.strip())

        chunks.append({
            "text": text,
            "timestamp": [round(start, 2), round(end, 2)]
        })
        full_text.append(text)
        prev_text = text

    return {"text": " ".join(full_text), "chunks": chunks}


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


def to_clean_srt(chunks: list) -> str:
    lines = []
    for i, chunk in enumerate(chunks, 1):
        start, end = chunk["timestamp"]
        text = chunk["text"].strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_fmt_time(start)} --> {_fmt_time(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def to_timestamped_text(chunks: list) -> str:
    lines = []
    for chunk in chunks:
        start, end = chunk["timestamp"]
        text = chunk["text"].strip()
        if text:
            lines.append(f"[{start:.1f}s - {end:.1f}s] {text}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="YouTube 자막 추출")
    parser.add_argument("--url", required=True, help="YouTube URL")
    parser.add_argument("--output", required=True, help="출력 디렉토리")
    parser.add_argument("--lang", default="ko", help="자막 언어 (기본: ko)")
    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("output/logs", exist_ok=True)

    print(f"=== YouTube 자막 추출 ===")
    print(f"URL: {args.url}")
    print(f"언어: {args.lang}")
    print(f"컨테이너: {'예' if is_container_env() else '아니오'}")
    cookie_browser = get_cookie_browser()
    if cookie_browser:
        print(f"쿠키 브라우저: {cookie_browser}")
    else:
        cookie_file = get_cookie_file()
        if cookie_file:
            print(f"쿠키 파일: {cookie_file}")
        else:
            print("쿠키: 없음 (봇 감지 시 cookies.txt 필요)")
    proxy = get_proxy()
    if proxy:
        print(f"프록시: {proxy}")
    print()

    srt_path = extract_subtitles(args.url, output_dir, args.lang)

    if not srt_path:
        print("\nERROR: 자막을 추출할 수 없습니다.")
        print("가능한 원인:")
        print("  - 해당 영상에 자막이 없음")
        print("  - 봇 감지 차단 -> cookies.txt 배치 또는 브라우저 로그인 후 재시도")
        print("  - 네트워크 오류 -> YT_PROXY 설정 확인")
        print("  - 상세 로그: output/logs/")
        sys.exit(1)

    print("\n자막 파싱 중...")
    transcript = parse_srt_to_transcript(srt_path)
    chunks = transcript.get("chunks", [])

    if not chunks:
        print("ERROR: 자막 파싱 결과가 비어있습니다.")
        sys.exit(1)

    json_path = os.path.join(output_dir, "transcript.json")
    clean_srt_path = os.path.join(output_dir, "transcript.srt")
    txt_path = os.path.join(output_dir, "transcript_timestamped.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    with open(clean_srt_path, "w", encoding="utf-8") as f:
        f.write(to_clean_srt(chunks))
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(to_timestamped_text(chunks))

    if srt_path != clean_srt_path and os.path.exists(srt_path):
        os.remove(srt_path)

    total_duration = chunks[-1]["timestamp"][1] if chunks else 0
    print(f"\n=== 자막 추출 완료 ===")
    print(f"세그먼트: {len(chunks)}개")
    print(f"총 길이: {total_duration:.0f}초 ({total_duration / 60:.1f}분)")
    print(f"JSON: {json_path}")
    print(f"SRT:  {clean_srt_path}")
    print(f"TXT:  {txt_path}")


if __name__ == "__main__":
    main()
