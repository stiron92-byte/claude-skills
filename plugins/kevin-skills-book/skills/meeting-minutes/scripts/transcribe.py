#!/usr/bin/env python3
"""음성 → 번호 붙은 발언(T0001…) 변환. 로컬 faster-whisper를 쓰며 음성은 외부로 보내지 않는다.

출력(--out-dir, 기본: 입력 파일 옆 <이름>_transcript/)
  transcript.txt   한 줄에 발언 하나: "T0001 [00:00:12] 텍스트"   ← 회의록 근거(발언 번호)로 인용한다
  transcript.json  {meta, segments:[{id, start, end, speaker, text, avg_logprob, no_speech_prob, low_confidence}]}

모델 선택(--model auto, 기본)
  사용자 맞춤 settings.yaml의 stt_model이 있으면 그것. 없으면 한국어는 small, 영어는 base를 고른다.
  선택한 모델이 아직 없고 디스크 여유가 모자라면, 이미 받아 둔 모델 중 가장 큰 것으로 바꾸고 이유를 출력한다.
  모델 크기(내려받기): tiny 75MB, base 145MB, small 465MB, medium 1.5GB, large-v3-turbo 1.6GB

용어 사전(--glossary 또는 오버라이드 references/glossary.md)
  참석자 이름·제품명·약어 목록. 기본은 회의록 단계의 교정 참고로만 쓴다(transcript.json meta.glossary_terms).
  --hotwords를 주면 인식 힌트로도 넘긴다. 실측: 이름 오인식은 줄었지만(샘플 4/4), 다른 녹음에서는 발언이 뭉치고
  숫자를 잘못 들었다(base: '총 3억'→'총 4월'). 숫자가 중요한 회의에는 켜지 않는다.

긴 녹음
  발언을 받는 즉시 파일에 쓴다. 중간에 끊기면 --resume으로 마지막 발언 이후부터 이어서 변환한다.

사용법
  python transcribe.py <음성파일> [--out-dir 폴더] [--language ko|en|auto] [--model auto|base|small|...]
                       [--glossary 용어.md] [--hotwords] [--resume] [--json]
마지막 줄: TRANSCRIBE DONE segments=<n> duration=<초> low_confidence=<n> model=<모델>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent / "_vendor"))

SUPPORTED = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".mp4", ".aac", ".flac", ".wma"}
MODEL_MB = {"tiny": 75, "base": 145, "small": 465, "medium": 1500, "large-v3-turbo": 1600, "large-v3": 3100}
ORDER = ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"]
# CPU int8 기준 1분 음성당 걸리는 분. base는 실측(샘플 3개 평균 약 5초), 나머지는 추정. 모델 내려받기 시간은 별도
SPEED = {"tiny": 0.05, "base": 0.09, "small": 0.3, "medium": 0.9, "large-v3-turbo": 0.6, "large-v3": 1.6}
LOW_LOGPROB = -1.0


def ts(sec: float) -> str:
    s = int(sec)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def decode_audio(path: Path, start: float = 0.0):
    """PyAV로 16kHz 모노 float32 배열을 만든다.
    faster-whisper 1.2.1의 decode_audio는 PyAV 15 이상에서 없어진 인자(metadata_errors)를 넘겨 실패하므로 직접 디코딩한다."""
    import av
    import numpy as np
    chunks = []
    with av.open(str(path)) as c:
        stream = c.streams.audio[0]
        rs = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in c.decode(stream):
            for o in rs.resample(frame):
                chunks.append(o.to_ndarray().reshape(-1))
        for o in rs.resample(None):
            chunks.append(o.to_ndarray().reshape(-1))
    audio = (np.concatenate(chunks).astype(np.float32) / 32768.0) if chunks else np.zeros(0, dtype=np.float32)
    return audio[int(start * 16000):]


def hf_cache() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"


def cached_models() -> list[str]:
    root = hf_cache()
    out = []
    for name in ORDER:
        d = root / f"models--Systran--faster-whisper-{name}"
        if d.is_dir() and any(d.glob("snapshots/*/model.bin")):
            out.append(name)
        elif name == "large-v3-turbo" and any(root.glob("models--*large-v3-turbo*/snapshots/*/model.bin")):
            out.append(name)
    return out


def user_settings() -> dict:
    try:
        import overrides
        return overrides.settings("meeting-minutes", SKILL_DIR)["settings"]
    except Exception:
        return {}


def pick_model(requested: str, language: str) -> tuple[str, str]:
    if requested != "auto":
        return requested, "사용자 지정"
    st = user_settings().get("stt_model")
    want = st or ("base" if language == "en" else "small")
    why = "사용자 맞춤 settings(stt_model)" if st else ("영어 기본" if language == "en" else "한국어 기본(base는 한국어 정확도가 낮다)")
    have = cached_models()
    if want in have:
        return want, why
    root = hf_cache()
    root.mkdir(parents=True, exist_ok=True)
    free_mb = shutil.disk_usage(root).free / 1e6
    if free_mb > MODEL_MB.get(want, 500) * 1.5 + 200:
        return want, why + " — 처음 쓰는 모델이라 내려받는다"
    if have:
        best = max(have, key=ORDER.index)
        return best, (f"{want} 모델을 받을 디스크 여유가 없어({free_mb:.0f}MB) 이미 받아 둔 {best}를 쓴다 — 정확도가 낮을 수 있으니 결과에 알릴 것")
    return want, why + f" — 디스크 여유 {free_mb:.0f}MB, 내려받기가 실패할 수 있다"


def load_glossary(path: str | None) -> tuple[str | None, str | None]:
    p = Path(path) if path else None
    src = "지정 파일"
    if p is None:
        try:
            import overrides
            found = overrides.resolve("meeting-minutes", "references/glossary.md", SKILL_DIR)
            p, src = (Path(found["path"]), f"사용자 맞춤({found['source']})") if found["path"] else (None, None)
        except Exception:
            p = None
    if p is None or not p.is_file():
        return None, None
    words = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = re.sub(r"^[-*#\s]+", "", line).strip()
        if line and not line.startswith(">"):
            words += [w.strip() for w in re.split(r"[,:|·]", line) if 1 < len(w.strip()) <= 30]
    words = list(dict.fromkeys(words))[:60]
    return (" ".join(words) if words else None), src


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="음성 → 번호 붙은 발언")
    ap.add_argument("input", nargs="?")
    ap.add_argument("--input", dest="input_opt", help="(이전 버전 호환)")
    ap.add_argument("--output", help="(이전 버전 호환) 출력 txt 경로 — 같은 폴더에 transcript.json도 쓴다")
    ap.add_argument("--out-dir")
    ap.add_argument("--language", default="ko", choices=["ko", "en", "auto"])
    ap.add_argument("--model", default="auto")
    ap.add_argument("--glossary")
    ap.add_argument("--hotwords", action="store_true", help="용어 사전을 인식 힌트로도 넘긴다(숫자 인식이 나빠질 수 있음)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    src = Path(a.input or a.input_opt or "")
    if not src.is_file():
        print(f"오류: 음성 파일이 없습니다: {src}")
        return 1
    if src.suffix.lower() not in SUPPORTED:
        print(f"오류: 지원하지 않는 형식 {src.suffix}. 지원: {', '.join(sorted(SUPPORTED))}")
        return 1
    out_dir = Path(a.out_dir) if a.out_dir else (Path(a.output).parent if a.output else src.with_name(src.stem + "_transcript"))
    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path = Path(a.output) if a.output else out_dir / "transcript.txt"
    json_path = out_dir / "transcript.json"

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("오류: faster-whisper가 없습니다. 설치: python -m pip install -r <스킬>/scripts/requirements.txt\n"
              "음성 변환이 어렵다면 클로바노트·노션 등에서 받은 텍스트를 prepare_transcript.py로 넣어도 된다.")
        return 1

    model_name, why = pick_model(a.model, a.language)
    t0 = time.time()
    audio_full = decode_audio(src)
    duration = len(audio_full) / 16000
    prev: list[dict] = []
    start = 0.0
    if a.resume and json_path.is_file():
        old = json.loads(json_path.read_text(encoding="utf-8"))
        prev = old.get("segments", [])
        start = prev[-1]["end"] if prev else 0.0
        print(f"이어하기: 발언 {len(prev)}개, {ts(start)}부터")
    est = duration / 60 * SPEED.get(model_name, 0.5)
    print(f"파일: {src.name} ({src.stat().st_size / 1e6:.1f}MB, {ts(duration)}) · 모델 {model_name}({why}) · 예상 약 {max(est, 0.2):.1f}분")
    if duration > 3600:
        print("주의: 1시간이 넘는 녹음이다. 끊기면 --resume으로 이어서 변환할 수 있다.")
    terms, gsrc = load_glossary(a.glossary)
    hot = terms if (terms and a.hotwords) else None
    if terms:
        how = "인식 힌트 + 교정 참고" if hot else "교정 참고(인식 힌트는 --hotwords)"
        print(f"용어 사전 적용({gsrc}, {how}): {terms[:80]}{'…' if len(terms) > 80 else ''}")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    audio = audio_full[int(start * 16000):]
    segments, info = model.transcribe(audio, language=None if a.language == "auto" else a.language, beam_size=5,
                                      vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
                                      hotwords=hot, condition_on_previous_text=False)
    lang = info.language
    segs = list(prev)
    n0 = len(prev)
    mode = "a" if prev and txt_path.is_file() else "w"
    with open(txt_path, mode, encoding="utf-8") as f:
        for s in segments:
            text = s.text.strip()
            if not text:
                continue
            i = len(segs) + 1
            low = s.avg_logprob < LOW_LOGPROB or s.no_speech_prob > 0.6 or s.compression_ratio > 2.4
            seg = {"id": f"T{i:04d}", "start": round(s.start + start, 2), "end": round(s.end + start, 2), "speaker": None,
                   "text": text, "avg_logprob": round(s.avg_logprob, 3), "no_speech_prob": round(s.no_speech_prob, 3),
                   "low_confidence": bool(low)}
            segs.append(seg)
            f.write(f"{seg['id']} [{ts(seg['start'])}]{' (?)' if low else ''} {text}\n")
            f.flush()
            if (i - n0) % 20 == 0:
                print(f"  진행: 발언 {i}개, {ts(seg['end'])} / {ts(duration)}")
            json_path.write_text(json.dumps({"meta": {}, "segments": segs}, ensure_ascii=False), encoding="utf-8") if (i - n0) % 20 == 0 else None
    low_n = sum(1 for s in segs if s["low_confidence"])
    meta = {"source": str(src.resolve()), "kind": "audio", "model": model_name, "model_reason": why, "language": lang,
            "duration_sec": round(duration, 1), "segments": len(segs), "low_confidence": low_n,
            "glossary": gsrc, "glossary_terms": terms.split() if terms else [], "hotwords": bool(hot), "elapsed_sec": round(time.time() - t0, 1)}
    json_path.write_text(json.dumps({"meta": meta, "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"출력: {txt_path}  ({len(segs)}개 발언, 확인 필요 {low_n}개 — 줄 끝 (?) 표시)")
    if a.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"TRANSCRIBE DONE segments={len(segs)} duration={duration:.0f} low_confidence={low_n} model={model_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
