#!/usr/bin/env python3
"""M2: transcribe.py가 고정 환경에서 mp3를 번호 붙은 발언으로 바꾸고, 이어하기·용어 사전·이전 인자 호환을 지원하며,
한국어 녹음의 핵심어를 담는지 확인한다.

faster-whisper가 있는 Python이 필요하다: 환경변수 MM_PYTHON → .workspace/pins-venv → 현재 Python 순서로 찾는다.
CI처럼 없는 환경에서는 --allow-missing이면 'TRANSCRIBE SKIPPED'를 출력하고 0으로 끝난다(게이트는 이 옵션 없이 돈다).
모델은 재현성을 위해 base로 고정한다(내려받기 145MB, 이미 받아 둔 경우 재사용).

양성 대조
- 같은 핵심어 비교를 다른 회의(영어 녹음) 변환 결과에 적용하면 재현율이 기준 미만이어야 한다.
- faster-whisper 자체 decode_audio가 이 환경에서 실패하는지 기록한다(직접 디코딩이 필요한 이유).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _meeting_fixtures import AUDIO, SCRIPTS, VENV_PY  # noqa: E402

KEYWORDS = ["스프린트", "로그인", "금요일", "수요일", "목요일", "70%", "소셜", "카카오", "회원", "비밀번호", "이메일", "기획서", "다음 회의"]
MIN_RECALL = 0.8


def find_python() -> str | None:
    cands = [os.environ.get("MM_PYTHON"), str(VENV_PY) if VENV_PY.is_file() else None, sys.executable]
    for c in [c for c in cands if c]:
        r = subprocess.run([c, "-c", "import faster_whisper, av"], capture_output=True)
        if r.returncode == 0:
            return c
    return None


def run(py: str, *args, timeout=1200) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([py, str(SCRIPTS / "transcribe.py"), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=timeout)


def recall(text: str) -> float:
    return sum(1 for k in KEYWORDS if k in text) / len(KEYWORDS)


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    py = find_python()
    if py is None:
        if "--allow-missing" in argv:
            print("TRANSCRIBE SKIPPED — faster-whisper가 있는 Python이 없다(CI). 로컬 게이트에서 검증한다")
            return 0
        print("TRANSCRIBE FAILED — faster-whisper가 있는 Python을 찾지 못했다(MM_PYTHON 또는 .workspace/pins-venv)")
        return 1
    fails: list[str] = []
    ko, en = AUDIO / "test_sprint_meeting_ko.mp3", AUDIO / "test_project_meeting_en.mp3"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        T = Path(td)
        r = run(py, ko, "--out-dir", T / "ko", "--language", "ko", "--model", "base")
        if "TRANSCRIBE DONE" not in r.stdout:
            print(r.stdout[-800:], r.stderr[-1500:])
            print("TRANSCRIBE FAILED — 한국어 녹음 변환 실패")
            return 1
        data = json.loads((T / "ko" / "transcript.json").read_text(encoding="utf-8"))
        meta, segs = data["meta"], data["segments"]
        txt = (T / "ko" / "transcript.txt").read_text(encoding="utf-8")
        if meta.get("kind") != "audio" or meta.get("model") != "base" or abs(meta.get("duration_sec", 0) - 148) > 3:
            fails.append(f"meta {meta}")
        if [s["id"] for s in segs] != [f"T{i:04d}" for i in range(1, len(segs) + 1)] or len(segs) < 20:
            fails.append(f"발언 번호·개수 {len(segs)}")
        if not all(l.startswith("T") and "] " in l for l in txt.splitlines()):
            fails.append("transcript.txt 줄 형식이 'T0001 [hh:mm:ss] 텍스트'가 아니다")
        if not all({"avg_logprob", "no_speech_prob", "low_confidence", "start", "end"} <= set(s) for s in segs):
            fails.append("발언에 신뢰도·시각 필드가 없다")
        rk = recall(" ".join(s["text"] for s in segs))
        if rk < MIN_RECALL:
            fails.append(f"핵심어 재현율 {rk:.2f} < {MIN_RECALL}")
        # 이어하기: 앞 10개만 남기고 다시 실행
        rd = T / "resume"
        rd.mkdir()
        first10 = segs[:10]
        (rd / "transcript.json").write_text(json.dumps({"meta": {}, "segments": first10}, ensure_ascii=False), encoding="utf-8")
        (rd / "transcript.txt").write_text("\n".join(l for l in txt.splitlines()[:10]) + "\n", encoding="utf-8")
        r2 = run(py, ko, "--out-dir", rd, "--language", "ko", "--model", "base", "--resume")
        d2 = json.loads((rd / "transcript.json").read_text(encoding="utf-8"))["segments"]
        if "이어하기" not in r2.stdout or d2[:10] != first10 or len(d2) < 20 or \
                [s["id"] for s in d2] != [f"T{i:04d}" for i in range(1, len(d2) + 1)] or d2[10]["start"] < first10[-1]["end"] - 0.5:
            fails.append(f"이어하기 실패: {r2.stdout[-300:]} 발언 {len(d2)}")
        # 용어 사전 + 이전 인자(--input/--output) 호환
        g = T / "glossary.md"
        g.write_text("# 참석자\n- 김PM, 이개발, 박디자인, 정기획\n# 용어\n- 퍼블리싱, AWS SES, 이월\n", encoding="utf-8")
        r3 = run(py, "--input", ko, "--output", T / "legacy" / "out.txt", "--language", "ko", "--model", "base", "--glossary", g, "--hotwords")
        if "용어 사전 적용" not in r3.stdout or not (T / "legacy" / "out.txt").is_file() or not (T / "legacy" / "transcript.json").is_file():
            fails.append(f"용어 사전·이전 인자 호환 실패: {r3.stdout[-300:]}")
        lm = json.loads((T / "legacy" / "transcript.json").read_text(encoding="utf-8"))["meta"] if (T / "legacy" / "transcript.json").is_file() else {}
        if not lm.get("hotwords") or "김PM" not in lm.get("glossary_terms", []):
            fails.append(f"--hotwords 기록 실패: {lm.get('hotwords')}, {lm.get('glossary_terms')}")
        # 기본(--hotwords 없음): 사전은 교정 참고로만 기록되고 인식 힌트로는 넘기지 않는다
        r5 = run(py, ko, "--out-dir", T / "gl_default", "--language", "ko", "--model", "base", "--glossary", g)
        dm = json.loads((T / "gl_default" / "transcript.json").read_text(encoding="utf-8"))["meta"]
        if dm.get("hotwords") or not dm.get("glossary_terms") or "교정 참고" not in r5.stdout:
            fails.append(f"기본 용어 사전 처리 실패: hotwords={dm.get('hotwords')}, terms={dm.get('glossary_terms')}")
        gl = (T / "legacy" / "out.txt").read_text(encoding="utf-8") if (T / "legacy" / "out.txt").is_file() else ""
        fixed = [w for w in ("김PM", "정기획", "퍼블리싱", "SES") if w in gl]
        # 오류 처리
        bad = T / "memo.pdf"
        bad.write_bytes(b"%PDF")
        if run(py, bad, "--out-dir", T / "x").returncode == 0 or run(py, T / "none.mp3", "--out-dir", T / "x").returncode == 0:
            fails.append("지원하지 않는 형식·없는 파일을 오류로 처리하지 않았다")
        # 양성 대조: 영어 회의 변환 결과에는 한국어 핵심어가 거의 없어야 한다
        r4 = run(py, en, "--out-dir", T / "en", "--language", "en", "--model", "base")
        en_text = (T / "en" / "transcript.txt").read_text(encoding="utf-8") if (T / "en" / "transcript.txt").is_file() else ""
        if "TRANSCRIBE DONE" not in r4.stdout or recall(en_text) >= MIN_RECALL or "Sarah" not in en_text:
            fails.append(f"양성 대조 실패: 영어 녹음 재현율 {recall(en_text):.2f}")
        # 라이브러리 결함 기록(직접 디코딩이 필요한 이유)
        lib = subprocess.run([py, "-c", f"from faster_whisper import decode_audio; decode_audio(r'{ko}')"], capture_output=True, text=True)
        lib_note = "faster-whisper decode_audio 실패(직접 디코딩 필요)" if lib.returncode != 0 and "metadata_errors" in lib.stderr else "faster-whisper decode_audio 정상(라이브러리 수정됨)"
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"TRANSCRIBE FAILED ({len(fails)})")
        return 1
    print(f"참고: {lib_note}; 용어 사전 적용 후 인식된 용어 {fixed}")
    print(f"TRANSCRIBE OK — 발언 {len(segs)}개, 핵심어 재현율 {rk:.2f}, 이어하기·용어 사전·이전 인자 호환·오류 처리·양성 대조 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
