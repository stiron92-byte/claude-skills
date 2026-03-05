#!/usr/bin/env python3
"""나레이션 영상 생성 파이프라인 오케스트레이터

전체 흐름:
  Phase 0: 환경 설정 (setup.sh)
  Phase 1: 텍스트 준비 (세그먼트 분할)
  Phase 2: 이미지 생성 (Gemini API)
  Phase 3: TTS 나레이션 생성 (Gemini TTS)
  Phase 4: 자막 타임스탬프 생성
  Phase 4.5: BGM 자동 생성 (무드 분석)
  Phase 5: FFmpeg 영상 합성
  Phase 6: 결과 보고
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def check_gemini_connectivity():
    """Gemini API 연결 가능 여부 확인 (컨테이너 네트워크 차단 감지)"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[WARN] GEMINI_API_KEY 미설정")
        return False

    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[WARN] Gemini API 연결 실패: {e}")
        return False


def install_fallback_deps():
    """오프라인 모드 의존성 자동 설치 (Pillow, edge-tts)"""
    deps = {"PIL": "Pillow", "edge_tts": "edge-tts"}

    for module, package in deps.items():
        try:
            __import__(module)
        except ImportError:
            print(f"  {package} 설치 중...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", package],
                capture_output=True, timeout=120,
            )

# 이미지 스타일 프리셋
IMAGE_STYLE_PRESETS = {
    "minimal": {
        "name": "미니멀 일러스트",
        "style": "minimal illustration, soft pastel colors, clean white background, simple shapes",
    },
    "watercolor": {
        "name": "수채화",
        "style": "delicate watercolor painting, soft bleeding edges, natural pigment texture, gentle color washes on textured paper",
    },
    "ghibli": {
        "name": "지브리 / 로파이 애니메이션",
        "style": "lo-fi anime style, Studio Ghibli inspired, warm hand-painted background, soft lighting, nostalgic and dreamy atmosphere",
    },
    "clay3d": {
        "name": "소프트 3D / 클레이",
        "style": "soft 3D render, clay material, rounded shapes, warm ambient occlusion, pastel tones, toy-like miniature diorama",
    },
    "impressionist": {
        "name": "인상파 유화",
        "style": "impressionist oil painting, visible brushstrokes, vibrant natural light, Monet-inspired color palette, dreamy atmosphere",
    },
    "flat": {
        "name": "플랫 디자인",
        "style": "modern flat design illustration, bold geometric shapes, limited color palette, clean vector art, no gradients",
    },
    "pencil": {
        "name": "연필 스케치",
        "style": "detailed pencil sketch, hand-drawn crosshatching, graphite texture, elegant black and white with subtle shading",
    },
    "cyberpunk": {
        "name": "사이버펑크 네온",
        "style": "cyberpunk neon art, glowing neon lights, dark background, vibrant magenta and cyan, futuristic cityscape atmosphere",
    },
    "retro": {
        "name": "빈티지 레트로 포스터",
        "style": "vintage retro poster art, muted earth tones, aged paper texture, mid-century illustration style, screen print aesthetic",
    },
    "cinematic": {
        "name": "포토리얼리스틱 / 시네마틱",
        "style": "photorealistic cinematic still, dramatic volumetric lighting, shallow depth of field, golden hour, film grain, movie poster quality",
    },
}


def run_command(cmd, description, timeout=600):
    """명령어 실행 및 결과 반환"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    start_time = time.time()

    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        capture_output=True, text=True, timeout=timeout,
        cwd=PROJECT_DIR,
    )

    elapsed = time.time() - start_time

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        if result.stderr:
            print(f"[STDERR] {result.stderr[:1000]}")
        print(f"[FAIL] {description} (소요: {elapsed:.1f}초)")
        return False

    print(f"[OK] {description} (소요: {elapsed:.1f}초)")
    return True


def phase0_setup(skip=False):
    """Phase 0: 환경 설정"""
    if skip:
        print("\n[SKIP] Phase 0: 환경 설정")
        return True

    setup_script = os.path.join(SCRIPT_DIR, "setup.sh")
    return run_command(
        ["bash", setup_script],
        "Phase 0: 환경 설정"
    )


def phase1_prepare_text(input_path, config_path, output_dir):
    """Phase 1: 텍스트 준비 및 세그먼트 분할"""
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    max_chars = config.get("SEGMENT_MAX_CHARS", 200)
    language = config.get("LANGUAGE", "ko")

    print(f"\n{'='*60}")
    print(f"  Phase 1: 텍스트 준비")
    print(f"{'='*60}")

    # 입력이 파일 경로인지 확인
    if os.path.isfile(input_path):
        with open(input_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        print(f"  입력 파일: {input_path}")
    else:
        raw_text = input_path
        print(f"  직접 입력 텍스트 ({len(raw_text)}자)")

    # 텍스트를 세그먼트로 분할
    segments = split_text_to_segments(raw_text, max_chars, language)

    # segments.json 저장
    segments_path = os.path.join(output_dir, "segments.json")
    with open(segments_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"  세그먼트 수: {len(segments)}개")
    print(f"  출력: {segments_path}")

    for i, seg in enumerate(segments):
        print(f"  [{i+1}] {seg['text'][:60]}...")

    print(f"\n[OK] Phase 1: 텍스트 준비 완료")
    return True


def split_text_to_segments(text, max_chars=200, language="ko"):
    """텍스트를 세그먼트로 분할

    분할 우선순위:
    1. 빈 줄(단락) 기준
    2. 문장 부호(. ! ? 。) 기준
    3. 최대 글자수 초과 시 강제 분할
    """
    # 빈 줄로 단락 분리
    paragraphs = re.split(r'\n\s*\n', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    segments = []
    for para in paragraphs:
        # 단락이 max_chars 이하면 그대로 세그먼트
        if len(para) <= max_chars:
            segments.append(para)
            continue

        # 문장 단위로 분리
        if language == "ko":
            sentences = re.split(r'(?<=[.!?。！？])\s*', para)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', para)

        current = ""
        for sent in sentences:
            if not sent.strip():
                continue
            if len(current) + len(sent) + 1 <= max_chars:
                current = (current + " " + sent).strip() if current else sent
            else:
                if current:
                    segments.append(current)
                # 문장 자체가 max_chars보다 긴 경우
                if len(sent) > max_chars:
                    # 콤마나 세미콜론 기준으로 추가 분할
                    parts = re.split(r'[,;，；]\s*', sent)
                    sub = ""
                    for part in parts:
                        if len(sub) + len(part) + 1 <= max_chars:
                            sub = (sub + ", " + part).strip(", ") if sub else part
                        else:
                            if sub:
                                segments.append(sub)
                            sub = part
                    if sub:
                        current = sub
                    else:
                        current = ""
                else:
                    current = sent
        if current:
            segments.append(current)

    result = []
    for i, text_seg in enumerate(segments):
        result.append({
            "index": i + 1,
            "text": text_seg,
            "image_prompt": "",  # generate_images.py에서 Gemini로 고품질 프롬프트 생성
        })

    return result


def phase2_generate_images(output_dir, config_path, skip=False, style_override=None, offline=False):
    """Phase 2: 이미지 생성"""
    if skip:
        print("\n[SKIP] Phase 2: 이미지 생성")
        return True

    segments_path = os.path.join(output_dir, "segments.json")
    segments_dir = os.path.join(output_dir, "segments")

    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "generate_images.py"),
        "--segments", segments_path,
        "--config", config_path,
        "--output", segments_dir,
    ]

    if style_override:
        cmd += ["--style", style_override]
    if offline:
        cmd += ["--offline"]

    return run_command(cmd, "Phase 2: 이미지 생성" + (" (오프라인)" if offline else ""))


def phase3_generate_tts(output_dir, config_path, skip=False, offline=False):
    """Phase 3: TTS 나레이션 생성"""
    if skip:
        print("\n[SKIP] Phase 3: TTS 나레이션 생성")
        return True

    segments_path = os.path.join(output_dir, "segments.json")
    segments_dir = os.path.join(output_dir, "segments")

    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "generate_tts.py"),
        "--segments", segments_path,
        "--config", config_path,
        "--output", segments_dir,
    ]
    if offline:
        cmd += ["--offline"]

    return run_command(cmd, "Phase 3: TTS 나레이션 생성" + (" (edge-tts)" if offline else ""))


def phase4_generate_subtitles(output_dir, config_path, skip=False, offline=False):
    """Phase 4: 자막 생성"""
    if skip:
        print("\n[SKIP] Phase 4: 자막 생성")
        return True

    segments_path = os.path.join(output_dir, "segments.json")
    segments_dir = os.path.join(output_dir, "segments")
    srt_path = os.path.join(output_dir, "subtitles.srt")

    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "generate_subtitles.py"),
        "--segments", segments_path,
        "--audio-dir", segments_dir,
        "--output", srt_path,
        "--config", config_path,
    ]
    if offline:
        cmd += ["--mode", "duration"]

    return run_command(cmd, "Phase 4: 자막 생성" + (" (duration 모드)" if offline else ""))


def phase4_5_generate_bgm(output_dir, config_path, mood=None, skip=False, offline=False):
    """Phase 4.5: 무드 기반 BGM 자동 생성"""
    if skip:
        print("\n[SKIP] Phase 4.5: BGM 자동 생성")
        return None

    segments_path = os.path.join(output_dir, "segments.json")
    bgm_output = os.path.join(output_dir, "bgm_auto.m4a")

    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "generate_bgm.py"),
        "--segments", segments_path,
        "--config", config_path,
        "--output", bgm_output,
    ]

    if mood:
        cmd += ["--mood", mood]
    if offline:
        cmd += ["--offline"]

    success = run_command(cmd, "Phase 4.5: BGM 자동 생성" + (" (오프라인)" if offline else ""))

    if success and os.path.exists(bgm_output):
        return bgm_output
    return None


def phase5_compose_video(output_dir, config_path, bgm_path=None, skip=False):
    """Phase 5: 영상 합성"""
    if skip:
        print("\n[SKIP] Phase 5: 영상 합성")
        return True

    segments_path = os.path.join(output_dir, "segments.json")
    segments_dir = os.path.join(output_dir, "segments")
    srt_path = os.path.join(output_dir, "subtitles.srt")
    final_video = os.path.join(output_dir, "final_video.mp4")

    cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "compose_video.py"),
        "--segments", segments_path,
        "--media-dir", segments_dir,
        "--srt", srt_path,
        "--config", config_path,
        "--output", final_video,
    ]

    if bgm_path:
        cmd += ["--bgm", bgm_path]

    return run_command(cmd, "Phase 5: 영상 합성")


def cleanup_intermediate_files(output_dir):
    """Phase 5 완료 후 중간 생성 파일 정리 (이미지, 오디오, 자막, BGM)"""
    import shutil

    print(f"\n{'='*60}")
    print(f"  중간 파일 정리")
    print(f"{'='*60}")

    removed = []

    # segments/ 디렉토리 (img_*.png, tts_*.wav)
    segments_dir = os.path.join(output_dir, "segments")
    if os.path.isdir(segments_dir):
        shutil.rmtree(segments_dir)
        removed.append(f"  - {segments_dir}/ (이미지/오디오)")

    # subtitles.srt
    srt_path = os.path.join(output_dir, "subtitles.srt")
    if os.path.exists(srt_path):
        os.remove(srt_path)
        removed.append(f"  - {srt_path}")

    # bgm_auto.m4a
    bgm_path = os.path.join(output_dir, "bgm_auto.m4a")
    if os.path.exists(bgm_path):
        os.remove(bgm_path)
        removed.append(f"  - {bgm_path}")

    if removed:
        print(f"  삭제된 파일:")
        for item in removed:
            print(item)
    else:
        print(f"  삭제할 중간 파일 없음")

    print(f"[OK] 중간 파일 정리 완료")


def phase6_report(output_dir):
    """Phase 6: 결과 보고"""
    print(f"\n{'='*60}")
    print(f"  Phase 6: 결과 보고")
    print(f"{'='*60}")

    final_video = os.path.join(output_dir, "final_video.mp4")
    segments_path = os.path.join(output_dir, "segments.json")

    report = {
        "status": "success",
        "output_video": final_video,
        "segments": [],
    }

    if os.path.exists(final_video):
        file_size = os.path.getsize(final_video)
        report["file_size_mb"] = round(file_size / 1024 / 1024, 1)

        # ffprobe로 길이 확인
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", final_video],
                capture_output=True, text=True, timeout=30
            )
            report["duration_seconds"] = round(float(probe.stdout.strip()), 1)
        except Exception:
            report["duration_seconds"] = 0

        print(f"  영상: {final_video}")
        print(f"  길이: {report['duration_seconds']}초 ({report['duration_seconds']/60:.1f}분)")
        print(f"  크기: {report['file_size_mb']}MB")
    else:
        report["status"] = "failed"
        print(f"  [ERROR] 영상 파일이 생성되지 않았습니다.")

    if os.path.exists(segments_path):
        with open(segments_path, "r", encoding="utf-8") as f:
            segments = json.load(f)
        report["segment_count"] = len(segments)
        report["segments"] = segments

        print(f"\n  세그먼트 상세:")
        for seg in segments:
            duration = seg.get("duration", 0)
            print(f"    [{seg['index']}] {seg['text'][:50]}... ({duration:.1f}초)")

    # metadata.json 저장
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  메타데이터: {metadata_path}")
    print(f"\n[OK] Phase 6: 결과 보고 완료")
    return report


def ask_image_style():
    """사용자에게 이미지 스타일 프리셋을 선택하도록 질의"""
    style_env = os.environ.get("IMAGE_STYLE_PRESET")
    if style_env and style_env in IMAGE_STYLE_PRESETS:
        preset = IMAGE_STYLE_PRESETS[style_env]
        print(f"[INFO] 환경변수 IMAGE_STYLE_PRESET 사용: {style_env} ({preset['name']})")
        return preset["style"]

    try:
        print("\n" + "=" * 60)
        print("  이미지 스타일 선택")
        print("=" * 60)

        keys = list(IMAGE_STYLE_PRESETS.keys())
        for i, key in enumerate(keys, 1):
            preset = IMAGE_STYLE_PRESETS[key]
            print(f"  {i:2d}. {preset['name']} ({key})")

        print(f"\n  번호를 입력하세요 (기본: 1 - 미니멀 일러스트)")
        choice = input("  선택: ").strip()

        if not choice:
            selected_key = keys[0]
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            selected_key = keys[int(choice) - 1]
        elif choice in IMAGE_STYLE_PRESETS:
            selected_key = choice
        else:
            print(f"  [WARN] 잘못된 입력 '{choice}', 기본값(미니멀) 사용")
            selected_key = keys[0]

        preset = IMAGE_STYLE_PRESETS[selected_key]
        print(f"  [OK] 스타일: {preset['name']}")
        print(f"       {preset['style'][:80]}...")
        return preset["style"]

    except (EOFError, KeyboardInterrupt):
        print("\n  [INFO] 기본 스타일(미니멀) 사용")
        return IMAGE_STYLE_PRESETS["minimal"]["style"]


def ask_bgm():
    """사용자에게 BGM 파일 경로를 질의"""
    bgm_env = os.environ.get("BGM_PATH")
    if bgm_env and os.path.exists(bgm_env):
        print(f"[INFO] 환경변수 BGM_PATH 사용: {bgm_env}")
        return bgm_env

    try:
        print("\n" + "="*60)
        print("  BGM(배경음악) 설정")
        print("="*60)
        print("  BGM 파일 경로를 입력하세요.")
        print("  (없으면 Enter를 눌러 건너뛰기)")
        bgm_input = input("  BGM 경로: ").strip()

        if bgm_input and os.path.exists(bgm_input):
            print(f"  [OK] BGM: {bgm_input}")
            return bgm_input
        elif bgm_input:
            print(f"  [WARN] 파일 없음: {bgm_input} - BGM 없이 진행")
        else:
            print("  [INFO] BGM 없이 진행")
    except (EOFError, KeyboardInterrupt):
        print("\n  [INFO] BGM 없이 진행")

    return None


def main():
    parser = argparse.ArgumentParser(
        description="나레이션 영상 생성 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 텍스트 파일로 영상 생성
  python3 scripts/run_pipeline.py --input templates/sample_quotes.txt

  # 직접 텍스트 입력
  python3 scripts/run_pipeline.py --input "성공은 준비된 자에게 온다."

  # 특정 설정으로 실행
  python3 scripts/run_pipeline.py --input input.txt --config templates/config.yaml

  # 특정 Phase만 실행
  python3 scripts/run_pipeline.py --input input.txt --only-phase 5
        """,
    )
    parser.add_argument("--input", required=True, help="텍스트 파일 경로 또는 직접 입력 텍스트")
    parser.add_argument("--config", default=os.path.join(PROJECT_DIR, "templates", "config.yaml"),
                        help="설정 파일 경로 (기본: templates/config.yaml)")
    parser.add_argument("--output-dir", default=os.path.join(PROJECT_DIR, "output"),
                        help="출력 디렉토리 (기본: output/)")
    parser.add_argument("--bgm", default=None, help="BGM 파일 경로")
    parser.add_argument("--skip-setup", action="store_true", help="Phase 0 건너뛰기")
    parser.add_argument("--skip-images", action="store_true", help="Phase 2 건너뛰기")
    parser.add_argument("--skip-tts", action="store_true", help="Phase 3 건너뛰기")
    parser.add_argument("--skip-subtitles", action="store_true", help="Phase 4 건너뛰기")
    parser.add_argument("--skip-compose", action="store_true", help="Phase 5 건너뛰기")
    parser.add_argument("--only-phase", type=int, help="특정 Phase만 실행 (0-6)")
    parser.add_argument("--no-bgm-prompt", action="store_true",
                        help="BGM 질의 건너뛰기 (무조건 BGM 없이 진행)")
    parser.add_argument("--auto-bgm", action="store_true", default=True,
                        help="무드 기반 BGM 자동 생성 (기본값: 활성)")
    parser.add_argument("--no-auto-bgm", action="store_true",
                        help="BGM 자동 생성 비활성화")
    parser.add_argument("--bgm-mood", default=None,
                        help="BGM 무드 직접 지정 (calm/inspirational/warm/dramatic/hopeful/meditative)")
    parser.add_argument("--image-style", default=None,
                        help="이미지 스타일 프리셋 또는 커스텀 스타일 문자열")
    parser.add_argument("--no-style-prompt", action="store_true",
                        help="이미지 스타일 질의 건너뛰기 (config.yaml 값 사용)")
    args = parser.parse_args()

    # 설정 파일 확인
    if not os.path.exists(args.config):
        # config_template.yaml에서 복사
        template = os.path.join(PROJECT_DIR, "templates", "config_template.yaml")
        if os.path.exists(template):
            import shutil
            shutil.copy2(template, args.config)
            print(f"[INFO] 설정 파일 생성: {args.config}")
        else:
            print(f"[ERROR] 설정 파일 없음: {args.config}")
            sys.exit(1)

    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, "segments"), exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, "logs"), exist_ok=True)

    # 이미지 스타일 설정
    style_override = None
    if args.image_style:
        # CLI에서 직접 지정: 프리셋 이름 또는 커스텀 문자열
        if args.image_style in IMAGE_STYLE_PRESETS:
            style_override = IMAGE_STYLE_PRESETS[args.image_style]["style"]
            print(f"[INFO] 이미지 스타일: {IMAGE_STYLE_PRESETS[args.image_style]['name']}")
        else:
            style_override = args.image_style
            print(f"[INFO] 커스텀 이미지 스타일: {style_override[:60]}...")
    elif not args.no_style_prompt:
        style_override = ask_image_style()

    # BGM 설정
    bgm_path = args.bgm
    use_auto_bgm = args.auto_bgm and not args.no_auto_bgm
    if not bgm_path and not use_auto_bgm and not args.no_bgm_prompt:
        bgm_path = ask_bgm()

    pipeline_start = time.time()

    # --- Gemini API 연결 확인 ---
    print("\n[CHECK] Gemini API 연결 확인 중...")
    offline_mode = not check_gemini_connectivity()
    if offline_mode:
        print("[MODE] 오프라인 모드 활성화 (Gemini API 차단 감지)")
        print("  → 이미지: PIL 텍스트 카드 (Pillow)")
        print("  → TTS: edge-tts (Microsoft)")
        print("  → 자막: 오디오 길이 기반 타이밍")
        print("  → BGM: 키워드 무드 감지")
        install_fallback_deps()
    else:
        print("[OK] Gemini API 연결 정상")

    print("\n" + "#"*60)
    print("#  나레이션 영상 자동 생성 파이프라인")
    if offline_mode:
        print("#  (오프라인 모드 - 로컬 폴백 사용)")
    print("#"*60)

    # --- 특정 Phase만 실행 ---
    if args.only_phase is not None:
        phase = args.only_phase
        if phase == 0:
            phase0_setup()
        elif phase == 1:
            phase1_prepare_text(args.input, args.config, args.output_dir)
        elif phase == 2:
            phase2_generate_images(args.output_dir, args.config, style_override=style_override)
        elif phase == 3:
            phase3_generate_tts(args.output_dir, args.config)
        elif phase == 4:
            phase4_generate_subtitles(args.output_dir, args.config)
        elif phase == 45:
            phase4_5_generate_bgm(args.output_dir, args.config, mood=args.bgm_mood)
        elif phase == 5:
            phase5_compose_video(args.output_dir, args.config, bgm_path)
        elif phase == 6:
            phase6_report(args.output_dir)
        else:
            print(f"[ERROR] 알 수 없는 Phase: {phase}")
            sys.exit(1)
        return

    # --- 전체 파이프라인 실행 ---
    success = True

    # Phase 0
    if not phase0_setup(skip=args.skip_setup):
        print("[WARN] Phase 0 실패, 계속 진행...")

    # Phase 1
    if not phase1_prepare_text(args.input, args.config, args.output_dir):
        print("[ERROR] Phase 1 실패 - 중단")
        sys.exit(1)

    # Phase 2
    if not phase2_generate_images(args.output_dir, args.config, skip=args.skip_images, style_override=style_override, offline=offline_mode):
        print("[ERROR] Phase 2 실패 - 중단")
        success = False

    # Phase 3
    if success and not phase3_generate_tts(args.output_dir, args.config, skip=args.skip_tts, offline=offline_mode):
        print("[ERROR] Phase 3 실패 - 중단")
        success = False

    # Phase 4
    if success and not phase4_generate_subtitles(args.output_dir, args.config, skip=args.skip_subtitles, offline=offline_mode):
        print("[WARN] Phase 4 실패, 자막 없이 계속 진행...")

    # Phase 4.5: BGM 자동 생성
    if success and not bgm_path and use_auto_bgm:
        auto_bgm = phase4_5_generate_bgm(args.output_dir, args.config, mood=args.bgm_mood, offline=offline_mode)
        if auto_bgm:
            bgm_path = auto_bgm
        else:
            print("[WARN] BGM 자동 생성 실패, BGM 없이 계속 진행...")

    # Phase 5
    if success and not phase5_compose_video(args.output_dir, args.config, bgm_path, skip=args.skip_compose):
        print("[ERROR] Phase 5 실패")
        success = False

    # Phase 5 완료 후 중간 파일 정리
    if success:
        cleanup_intermediate_files(args.output_dir)

    # Phase 6
    report = phase6_report(args.output_dir)

    elapsed = time.time() - pipeline_start
    print(f"\n{'#'*60}")
    print(f"#  파이프라인 완료 (총 소요: {elapsed:.1f}초 / {elapsed/60:.1f}분)")
    if success and report.get("status") == "success":
        print(f"#  최종 영상: {report.get('output_video', 'N/A')}")
    else:
        print(f"#  상태: 일부 실패")
    print(f"{'#'*60}")


if __name__ == "__main__":
    main()
