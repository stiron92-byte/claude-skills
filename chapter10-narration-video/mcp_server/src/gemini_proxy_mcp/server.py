#!/usr/bin/env python3
"""Gemini API Proxy + Host Processing MCP Server

호스트 머신에서 실행되어:
1. Gemini API에 직접 접근 (컨테이너 네트워크 차단 우회)
2. FFmpeg 기반 영상 합성/BGM 생성을 호스트에서 실행

Tools:
  - gemini_generate_image: 이미지 생성 (Gemini Image API)
  - gemini_generate_tts: TTS 음성 생성 (Gemini TTS API)
  - gemini_generate_text: 텍스트 생성 (Gemini Text API)
  - gemini_analyze_audio: 오디오 분석 (Gemini Audio API)
  - prepare_text: 텍스트 세그먼트 분할 (호스트)
  - generate_bgm: 무드 기반 BGM 생성 (호스트 FFmpeg)
  - compose_video: 영상 합성 (호스트 FFmpeg)
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
import wave

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("gemini-proxy")

# 스킬 루트 디렉토리 (mcp_server의 부모)
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_gemini_client():
    """Gemini API 클라이언트 생성"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
    from google import genai
    return genai.Client(api_key=api_key)


def _default_output_dir():
    """기본 출력 디렉토리 (~/Desktop/narration_output)"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.expanduser("~")
    return os.path.join(desktop, "narration_output")


@server.list_tools()
async def list_tools():
    return [
        # --- Gemini API 도구 ---
        Tool(
            name="gemini_generate_image",
            description="Gemini API로 이미지 생성. 프롬프트와 스타일을 받아 PNG 이미지를 지정 경로에 저장합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "이미지 생성 프롬프트 (영어)"},
                    "style": {"type": "string", "description": "아트 스타일 문자열"},
                    "output_path": {"type": "string", "description": "저장할 파일 경로 (.png)"},
                    "model": {"type": "string", "description": "모델명 (기본: gemini-2.5-flash-image)"},
                },
                "required": ["prompt", "style", "output_path"],
            },
        ),
        Tool(
            name="gemini_generate_tts",
            description="Gemini TTS API로 텍스트를 음성으로 변환. WAV 파일로 저장하고 재생 길이를 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "변환할 텍스트"},
                    "voice": {"type": "string", "description": "보이스 이름 (Kore, Aoede, Charon, Leda, Puck, Fenrir)"},
                    "style": {"type": "string", "description": "나레이션 스타일 지시 (선택)"},
                    "output_path": {"type": "string", "description": "저장할 파일 경로 (.wav)"},
                },
                "required": ["text", "voice", "output_path"],
            },
        ),
        Tool(
            name="gemini_generate_text",
            description="Gemini 텍스트 생성 API 호출. 프롬프트를 받아 텍스트 응답을 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "프롬프트"},
                    "model": {"type": "string", "description": "모델명 (기본: gemini-2.5-flash)"},
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="gemini_analyze_audio",
            description="Gemini 오디오 이해 API로 오디오 파일을 분석합니다. 타임스탬프 추출 등에 사용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_path": {"type": "string", "description": "분석할 오디오 파일 경로 (.wav)"},
                    "prompt": {"type": "string", "description": "분석 프롬프트"},
                    "model": {"type": "string", "description": "모델명 (기본: gemini-2.5-flash)"},
                },
                "required": ["audio_path", "prompt"],
            },
        ),
        # --- 호스트 파일/처리 도구 ---
        Tool(
            name="save_file",
            description="호스트 머신에 텍스트 파일을 저장합니다. SRT 자막 등 텍스트 파일을 호스트에 쓸 때 사용합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "저장할 파일 경로"},
                    "content": {"type": "string", "description": "파일 내용"},
                    "encoding": {"type": "string", "description": "인코딩 (기본: utf-8)"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="read_file",
            description="호스트 머신의 파일을 읽어 내용을 반환합니다. segments.json 등을 읽을 때 사용합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "읽을 파일 경로"},
                    "encoding": {"type": "string", "description": "인코딩 (기본: utf-8)"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="prepare_text",
            description="텍스트를 세그먼트로 분할합니다. 호스트에서 실행되며 segments.json을 생성합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_text": {"type": "string", "description": "분할할 텍스트 내용 (직접 전달)"},
                    "input_file": {"type": "string", "description": "입력 텍스트 파일 경로 (input_text 대신 사용)"},
                    "output_dir": {"type": "string", "description": "출력 디렉토리 (기본: ~/Desktop/narration_output)"},
                    "max_chars": {"type": "integer", "description": "세그먼트 최대 글자수 (기본: 200)"},
                },
                "required": [],
            },
        ),
        Tool(
            name="generate_bgm",
            description="무드 기반 앰비언트 BGM을 FFmpeg로 생성합니다. 호스트에서 실행됩니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "segments_json": {"type": "string", "description": "segments.json 파일 경로"},
                    "mood": {"type": "string", "description": "무드 (calm/inspirational/warm/dramatic/hopeful/meditative)"},
                    "output_path": {"type": "string", "description": "출력 BGM 파일 경로 (.m4a)"},
                    "duration": {"type": "number", "description": "BGM 길이(초). 0이면 자동 계산"},
                },
                "required": ["segments_json", "mood"],
            },
        ),
        Tool(
            name="compose_video",
            description="이미지+TTS+자막+BGM을 합성하여 최종 영상을 생성합니다. 호스트 FFmpeg로 실행됩니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "segments_json": {"type": "string", "description": "segments.json 파일 경로"},
                    "media_dir": {"type": "string", "description": "이미지/오디오가 저장된 디렉토리"},
                    "srt_path": {"type": "string", "description": "SRT 자막 파일 경로"},
                    "output_path": {"type": "string", "description": "최종 영상 출력 경로 (.mp4)"},
                    "bgm_path": {"type": "string", "description": "BGM 파일 경로 (선택)"},
                    "config_overrides": {
                        "type": "object",
                        "description": "설정 오버라이드 (RESOLUTION, FPS, FADE_DURATION, SEGMENT_GAP, BGM_VOLUME, FONT_SIZE)",
                    },
                },
                "required": ["segments_json", "media_dir", "srt_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "gemini_generate_image":
            return await _generate_image(arguments)
        elif name == "gemini_generate_tts":
            return await _generate_tts(arguments)
        elif name == "gemini_generate_text":
            return await _generate_text(arguments)
        elif name == "gemini_analyze_audio":
            return await _analyze_audio(arguments)
        elif name == "save_file":
            return await _save_file(arguments)
        elif name == "read_file":
            return await _read_file(arguments)
        elif name == "prepare_text":
            return await _prepare_text(arguments)
        elif name == "generate_bgm":
            return await _generate_bgm(arguments)
        elif name == "compose_video":
            return await _compose_video(arguments)
        else:
            return [TextContent(type="text", text=f"ERROR: Unknown tool: {name}")]
    except Exception as e:
        import traceback
        return [TextContent(type="text", text=f"ERROR: {str(e)}\n{traceback.format_exc()}")]


# =============================================================================
# Gemini API 도구 구현
# =============================================================================

async def _generate_image(args):
    """Gemini Image API로 이미지 생성"""
    client = get_gemini_client()
    from google.genai import types

    prompt = args["prompt"]
    style = args.get("style", "")
    output_path = args["output_path"]
    model = args.get("model", "gemini-2.5-flash-image")

    full_prompt = f"{prompt}. Art style: {style}. No text, no letters, no words in the image."

    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img_data = part.inline_data.data
            if isinstance(img_data, str):
                img_data = base64.b64decode(img_data)

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(img_data)

            file_size = os.path.getsize(output_path)
            return [TextContent(
                type="text",
                text=json.dumps({"status": "success", "path": output_path, "size_bytes": file_size}),
            )]

    return [TextContent(type="text", text=json.dumps({"status": "error", "message": "No image data in response"}))]


async def _generate_tts(args):
    """Gemini TTS API로 음성 생성"""
    client = get_gemini_client()
    from google.genai import types

    text = args["text"]
    voice = args.get("voice", "Aoede")
    style = args.get("style", "")
    output_path = args["output_path"]

    if style:
        tts_prompt = f"<speech_instructions>{style}</speech_instructions>\n\n{text}"
    else:
        tts_prompt = (
            "<speech_instructions>"
            "Speak naturally like a real person having a warm conversation. "
            "Use natural breathing pauses between sentences. "
            "Vary your pace slightly — slow down for emotional moments, "
            "and maintain a gentle, soothing rhythm overall."
            "</speech_instructions>\n\n"
            f"{text}"
        )

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
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

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(audio_data)

    with wave.open(output_path, "rb") as wf:
        duration = wf.getnframes() / wf.getframerate()

    return [TextContent(
        type="text",
        text=json.dumps({"status": "success", "path": output_path, "duration_seconds": round(duration, 1)}),
    )]


async def _generate_text(args):
    """Gemini 텍스트 생성"""
    client = get_gemini_client()

    prompt = args["prompt"]
    model = args.get("model", "gemini-2.5-flash")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    return [TextContent(type="text", text=response.text)]


async def _analyze_audio(args):
    """Gemini 오디오 분석"""
    client = get_gemini_client()

    audio_path = args["audio_path"]
    prompt = args["prompt"]
    model = args.get("model", "gemini-2.5-flash")

    uploaded_file = client.files.upload(file=audio_path)

    response = client.models.generate_content(
        model=model,
        contents=[prompt, uploaded_file],
    )

    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass

    return [TextContent(type="text", text=response.text)]


# =============================================================================
# 호스트 파일 도구 구현
# =============================================================================

async def _save_file(args):
    """호스트에 텍스트 파일 저장"""
    path = args["path"]
    content = args["content"]
    encoding = args.get("encoding", "utf-8")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)

    file_size = os.path.getsize(path)
    return [TextContent(
        type="text",
        text=json.dumps({"status": "success", "path": path, "size_bytes": file_size}),
    )]


async def _read_file(args):
    """호스트의 파일 읽기"""
    path = args["path"]
    encoding = args.get("encoding", "utf-8")

    if not os.path.exists(path):
        return [TextContent(type="text", text=json.dumps({"status": "error", "message": f"파일 없음: {path}"}))]

    with open(path, "r", encoding=encoding) as f:
        content = f.read()

    return [TextContent(
        type="text",
        text=json.dumps({"status": "success", "path": path, "content": content}, ensure_ascii=False),
    )]


# =============================================================================
# 호스트 처리 도구 구현
# =============================================================================

async def _prepare_text(args):
    """텍스트를 세그먼트로 분할"""
    import re
    import tempfile

    output_dir = args.get("output_dir", _default_output_dir())
    max_chars = args.get("max_chars", 200)

    # 입력 텍스트 결정
    if "input_text" in args and args["input_text"]:
        text = args["input_text"]
    elif "input_file" in args and args["input_file"]:
        with open(args["input_file"], "r", encoding="utf-8") as f:
            text = f.read()
    else:
        return [TextContent(type="text", text=json.dumps({"status": "error", "message": "input_text 또는 input_file이 필요합니다"}))]

    # 세그먼트 분할 로직 (run_pipeline.py의 로직 재현)
    text = text.strip()
    # 빈 줄로 구분된 단락들
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    segments = []
    for para in paragraphs:
        if len(para) <= max_chars:
            segments.append(para)
        else:
            # 문장 단위로 분할
            sentences = re.split(r'(?<=[.!?。！？])\s*', para)
            current = ""
            for sent in sentences:
                if not sent.strip():
                    continue
                if current and len(current) + len(sent) + 1 > max_chars:
                    segments.append(current.strip())
                    current = sent
                else:
                    current = f"{current} {sent}".strip() if current else sent
            if current.strip():
                segments.append(current.strip())

    # segments.json 생성
    os.makedirs(output_dir, exist_ok=True)
    segments_dir = os.path.join(output_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)

    segments_data = []
    for i, seg_text in enumerate(segments):
        segments_data.append({
            "index": i + 1,
            "text": seg_text,
            "image_prompt": "",
        })

    segments_path = os.path.join(output_dir, "segments.json")
    with open(segments_path, "w", encoding="utf-8") as f:
        json.dump(segments_data, f, ensure_ascii=False, indent=2)

    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "success",
            "segments_path": segments_path,
            "segment_count": len(segments_data),
            "output_dir": output_dir,
            "segments_dir": segments_dir,
            "segments": [{"index": s["index"], "text": s["text"][:60] + "..."} for s in segments_data],
        }, ensure_ascii=False),
    )]


async def _generate_bgm(args):
    """FFmpeg로 앰비언트 BGM 생성"""
    segments_json = args["segments_json"]
    mood = args.get("mood", "inspirational")
    output_path = args.get("output_path")
    duration = args.get("duration", 0)

    # segments.json 읽기
    with open(segments_json, "r", encoding="utf-8") as f:
        segments = json.load(f)

    # 기본 출력 경로
    if not output_path:
        output_path = os.path.join(os.path.dirname(segments_json), "bgm_auto.m4a")

    # scripts/generate_bgm.py 호출
    script_path = os.path.join(SKILL_DIR, "scripts", "generate_bgm.py")
    config_path = os.path.join(SKILL_DIR, "templates", "config.yaml")

    cmd = [
        sys.executable, script_path,
        "--segments", segments_json,
        "--config", config_path,
        "--output", output_path,
        "--mood", mood,
        "--offline",  # MCP에서는 Gemini 무드분석 불필요 (이미 Claude가 분석)
    ]
    if duration > 0:
        cmd += ["--duration", str(duration)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                            env={**os.environ, "PYTHONPATH": SKILL_DIR})

    if result.returncode != 0:
        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "message": result.stderr[-500:] if result.stderr else "BGM 생성 실패",
            "stdout": result.stdout[-300:] if result.stdout else "",
        }))]

    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "success",
            "path": output_path,
            "mood": mood,
            "size_bytes": file_size,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }),
    )]


async def _compose_video(args):
    """FFmpeg로 최종 영상 합성"""
    segments_json = args["segments_json"]
    media_dir = args["media_dir"]
    srt_path = args["srt_path"]
    output_path = args.get("output_path")
    bgm_path = args.get("bgm_path")
    config_overrides = args.get("config_overrides", {})

    # 기본 출력 경로: ~/Desktop/narration_output/final_video.mp4
    if not output_path:
        output_path = os.path.join(os.path.dirname(segments_json), "final_video.mp4")

    # config.yaml을 기반으로 임시 config 생성 (오버라이드 적용)
    config_path = os.path.join(SKILL_DIR, "templates", "config.yaml")

    # compose_video.py 직접 호출
    script_path = os.path.join(SKILL_DIR, "scripts", "compose_video.py")

    cmd = [
        sys.executable, script_path,
        "--segments", segments_json,
        "--media-dir", media_dir,
        "--srt", srt_path,
        "--config", config_path,
        "--output", output_path,
    ]
    if bgm_path:
        cmd += ["--bgm", bgm_path]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                            env={**os.environ, "PYTHONPATH": SKILL_DIR})

    if result.returncode != 0:
        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "message": result.stderr[-500:] if result.stderr else "영상 합성 실패",
            "stdout": result.stdout[-500:] if result.stdout else "",
        }))]

    # 결과 정보 수집
    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

    # ffprobe로 영상 길이 확인
    final_duration = 0
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", output_path],
            capture_output=True, text=True, timeout=30,
        )
        final_duration = float(probe.stdout.strip())
    except Exception:
        pass

    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "success",
            "path": output_path,
            "duration_seconds": round(final_duration, 1),
            "size_mb": round(file_size / 1024 / 1024, 1),
            "stdout": result.stdout[-500:] if result.stdout else "",
            "message": f"영상이 생성되었습니다: {output_path}",
        }),
    )]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
