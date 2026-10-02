#!/usr/bin/env python3
"""회의 텍스트 → 번호 붙은 발언(T0001…). 음성 변환 결과(transcribe.py)와 같은 형식을 만든다.

왜 번호를 붙이나: 회의록의 결정·할 일마다 "어느 발언에서 나왔는지"(근거)를 적어야 검증할 수 있다.
번호가 있으면 verify_minutes.py가 근거 발언을 찾아 담당자·기한·숫자를 대조한다.

지원 형식(자동 감지)
- 클로바노트 내보내기: 머리글(제목·날짜·참석자) + "화자 00:12" 줄 + 발언 줄
- 화자 표기: "김민지: 발언", "[00:01:02] 김민지: 발언", "김민지 (00:12): 발언"
- SRT / WebVTT(Zoom "이름: 발언", Teams "<v 이름>발언")
- transcribe.py 결과("T0001 [00:00:12] 발언")
- 그 밖의 일반 텍스트(문단·줄 단위)
- .docx(문단을 줄로 읽어 위 규칙 적용)
긴 발언(250자 초과)은 문장 단위로 나눠 번호를 따로 준다(근거를 정확히 가리키려고).

사용법: python prepare_transcript.py <파일 또는 -(표준입력)> --out-dir <폴더> [--json]
출력: transcript.txt, transcript.json (transcribe.py와 같은 구조)
마지막 줄: PREPARE DONE format=<형식> segments=<n> speakers=<n>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TIME = r"(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)"
CLOVA_HEAD = re.compile(r"^(?P<sp>[^\d\s:][^:]{0,24}?)\s+" + TIME + r"\s*$")
SPEAKER_LINE = re.compile(r"^(?:\[" + TIME + r"\]\s*)?(?P<sp>[^\s:\[\]][^:\[\]]{0,24}?)\s*(?:\(" + TIME + r"\))?\s*[:：]\s*(?P<text>.+)$")
TNUM = re.compile(r"^T(\d{3,5})\s+\[" + TIME + r"\]\s*(?:\(\?\)\s*)?(?:(?P<sp>[^:\]]{1,24}):\s)?(?P<text>.*)$")
SRT_TIME = re.compile(r"^" + TIME + r"\s*-->\s*" + TIME)
VTT_VOICE = re.compile(r"^<v\s+([^>]+)>(.*?)(?:</v>)?$")
URLISH = re.compile(r"^(https?://|www\.)")


def secs(t: str | None) -> float | None:
    if not t:
        return None
    t = t.replace(",", ".")
    parts = [float(x) for x in t.split(":")]
    return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0] * 3600 + parts[1] * 60 + parts[2]


def ts(sec: float | None) -> str:
    if sec is None:
        return "--:--:--"
    s = int(sec)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def read_text(p: str) -> str:
    if p == "-":
        return sys.stdin.read()
    path = Path(p)
    if path.suffix.lower() == ".docx":
        from docx import Document
        return "\n".join(par.text for par in Document(str(path)).paragraphs)
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect(lines: list[str]) -> str:
    ne = [l for l in lines if l.strip()]
    if not ne:
        return "empty"
    if ne[0].strip().upper().startswith("WEBVTT"):
        return "vtt"
    if sum(bool(SRT_TIME.match(l.strip())) for l in ne) >= 2:
        return "srt"
    if sum(bool(TNUM.match(l.strip())) for l in ne) >= max(2, len(ne) // 2):
        return "numbered"
    heads = [i for i, l in enumerate(lines) if CLOVA_HEAD.match(l.strip())]
    if len(heads) >= 2 and all(i + 1 < len(lines) and lines[i + 1].strip() for i in heads[:5]):
        return "clova"
    if sum(bool(SPEAKER_LINE.match(l.strip())) for l in ne) >= max(2, len(ne) * 0.4):
        return "speaker"
    return "plain"


def parse(text: str) -> tuple[str, list[dict], list[str]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    fmt = detect(lines)
    out: list[dict] = []
    header: list[str] = []
    if fmt == "clova":
        first = next(i for i, l in enumerate(lines) if CLOVA_HEAD.match(l.strip()))
        header = [l.strip() for l in lines[:first] if l.strip()]
        i = first
        while i < len(lines):
            m = CLOVA_HEAD.match(lines[i].strip())
            if m:
                body = []
                j = i + 1
                while j < len(lines) and not CLOVA_HEAD.match(lines[j].strip()):
                    if lines[j].strip():
                        body.append(lines[j].strip())
                    j += 1
                out.append({"speaker": m.group("sp").strip(), "start": secs(m.group(2)), "text": " ".join(body)})
                i = j
            else:
                i += 1
    elif fmt in ("srt", "vtt"):
        cur = None
        for l in lines:
            s = l.strip()
            m = SRT_TIME.match(s)
            if m:
                cur = {"speaker": None, "start": secs(m.group(1)), "end": secs(m.group(2)), "text": ""}
                out.append(cur)
                continue
            if cur is None or not s or s.isdigit() or s.upper().startswith(("WEBVTT", "NOTE")):
                continue
            v = VTT_VOICE.match(s)
            if v:
                cur["speaker"], s = v.group(1).strip(), re.sub(r"<[^>]+>", "", v.group(2)).strip()
            else:
                sm = SPEAKER_LINE.match(s)
                if sm and not cur["text"]:
                    cur["speaker"], s = sm.group("sp").strip(), sm.group("text").strip()
            s = re.sub(r"<[^>]+>", "", s)
            cur["text"] = (cur["text"] + " " + s).strip()
        out = [o for o in out if o["text"]]
        merged: list[dict] = []  # 같은 화자가 이어 말한 자막 조각은 합친다
        for o in out:
            if merged and o["speaker"] and merged[-1]["speaker"] == o["speaker"] and len(merged[-1]["text"]) < 200:
                merged[-1]["text"] += " " + o["text"]
                merged[-1]["end"] = o.get("end")
            else:
                merged.append(o)
        out = merged
    elif fmt == "numbered":
        for l in lines:
            m = TNUM.match(l.strip())
            if m:
                out.append({"speaker": (m.group("sp") or None), "start": secs(m.group(2)), "text": m.group("text").strip()})
    elif fmt == "speaker":
        for l in lines:
            s = l.strip()
            if not s:
                continue
            m = SPEAKER_LINE.match(s)
            if m and not URLISH.match(s):
                out.append({"speaker": m.group("sp").strip(), "start": secs(m.group(1) or m.group(3)), "text": m.group("text").strip()})
            elif out:
                out[-1]["text"] += " " + s  # 화자 표기 없는 줄은 앞 발언에 이어 붙인다
            else:
                header.append(s)
    else:
        for l in lines:
            if l.strip():
                out.append({"speaker": None, "start": None, "text": l.strip()})
    segs: list[dict] = []
    for o in out:
        pieces = [o["text"]]
        if len(o["text"]) > 250:
            pieces = [p.strip() for p in re.split(r"(?<=[.!?。다요죠])\s+", o["text"]) if p.strip()]
        for p in pieces:
            segs.append({"id": f"T{len(segs) + 1:04d}", "start": o.get("start"), "end": o.get("end"), "speaker": o.get("speaker"),
                         "text": p, "low_confidence": False})
    return fmt, segs, header


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="회의 텍스트 → 번호 붙은 발언")
    ap.add_argument("input")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.input != "-" and not Path(a.input).is_file():
        print(f"오류: 파일이 없습니다: {a.input}")
        return 1
    fmt, segs, header = parse(read_text(a.input))
    if not segs:
        print("오류: 발언을 찾지 못했습니다. 파일이 비어 있거나 텍스트가 아닙니다.")
        return 1
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    speakers = sorted({s["speaker"] for s in segs if s["speaker"]})
    with open(out / "transcript.txt", "w", encoding="utf-8") as f:
        for h in header:
            f.write(f"# {h}\n")
        for s in segs:
            f.write(f"{s['id']} [{ts(s['start'])}] {s['speaker'] + ': ' if s['speaker'] else ''}{s['text']}\n")
    meta = {"source": str(Path(a.input).resolve()) if a.input != "-" else "stdin", "kind": "text", "format": fmt,
            "header": header, "speakers": speakers, "segments": len(segs), "low_confidence": 0}
    (out / "transcript.json").write_text(json.dumps({"meta": meta, "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.json:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"출력: {out / 'transcript.txt'} — 형식 {fmt}, 발언 {len(segs)}개, 화자 {len(speakers)}명 {speakers}")
    print(f"PREPARE DONE format={fmt} segments={len(segs)} speakers={len(speakers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
