#!/usr/bin/env python3
"""M3: prepare_transcript.py가 여러 텍스트 형식을 같은 '번호 붙은 발언' 형식으로 바꾸는지 확인한다.

형식마다 화자·발언 수·첫 발언을 기대값과 대조한다. 양성 대조: 기대값을 일부러 틀리게 준 경우 비교가 실패해야 한다.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _meeting_fixtures import KEY, TEXT, run_script  # noqa: E402

CASES = {
    "speaker.txt": ("speaker", 3, ["김민지", "이준호"], "다음 주 월요일 오픈",
                    "김민지: 다음 주 월요일 오픈으로 하죠.\n이준호: 네, 쿠폰도 준비하겠습니다.\n이어서 말하면 이 줄은 앞 발언에 붙습니다.\n김민지: 좋아요. 끝내죠.\n"),
    "stamped.txt": ("speaker", 2, ["Sarah", "Mike"], "landing page",
                    "[00:00:03] Sarah: The landing page is ready.\n[00:00:09] Mike: The fix is in progress.\n"),
    "zoom.vtt": ("vtt", 2, ["김민지", "이준호"], "시작할게요",
                 "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.500\n김민지: 시작할게요.\n\n2\n00:00:04.000 --> 00:00:06.000\n이준호: 네.\n"),
    "teams.vtt": ("vtt", 2, ["Kim Minji", "Lee Junho"], "agenda",
                  "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<v Kim Minji>First agenda item.</v>\n\n00:00:03.500 --> 00:00:05.000\n<v Kim Minji>Then budget.</v>\n\n00:00:06.000 --> 00:00:08.000\n<v Lee Junho>Sounds good.</v>\n"),
    "sub.srt": ("srt", 2, [], "회의를 시작",
                "1\n00:00:01,000 --> 00:00:03,000\n회의를 시작하겠습니다.\n\n2\n00:00:03,500 --> 00:00:06,000\n첫 안건은 예산입니다.\n"),
    "numbered.txt": ("numbered", 3, [], "스프린트",
                     "T0001 [00:00:00] 스프린트 회의 시작하겠습니다.\nT0002 [00:00:04] (?) 참석자는 넷입니다.\nT0003 [00:00:12] 첫 안건입니다.\n"),
    "plain.txt": ("plain", 3, [], "회의 메모",
                  "오늘 회의 메모\n예산은 그대로 유지\n다음 주에 다시 보기\n"),
    "long.txt": ("speaker", 4, ["김민지", "이준호"], "첫째",
                 "김민지: " + "첫째 안건은 일정입니다. " + "이 문장은 길게 이어집니다. " * 20 + "\n이준호: 네.\n"),
}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    fails: list[str] = []

    def compare(res: dict, exp: tuple) -> list[str]:
        fmt, n, speakers, first = exp
        p = []
        if res["meta"]["format"] != fmt:
            p.append(f"형식 {res['meta']['format']} ≠ {fmt}")
        segs = res["segments"]
        if (len(segs) < n) if name_is_long else (len(segs) != n):
            p.append(f"발언 {len(segs)}개 ≠ {n}")
        if speakers and sorted(set(speakers)) != sorted(res["meta"]["speakers"]):
            p.append(f"화자 {res['meta']['speakers']} ≠ {speakers}")
        if first not in segs[0]["text"]:
            p.append(f"첫 발언에 '{first}' 없음: {segs[0]['text'][:40]}")
        ids = [s["id"] for s in segs]
        if ids != [f"T{i:04d}" for i in range(1, len(ids) + 1)]:
            p.append("발언 번호가 연속이 아니다")
        return p

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        T = Path(td)
        results = {}
        for name, (fmt, n, speakers, first, body) in CASES.items():
            (T / name).write_text(body, encoding="utf-8")
            out = T / (name + "_out")
            r = run_script("prepare_transcript.py", T / name, "--out-dir", out)
            if r.returncode != 0:
                fails.append(f"{name}: 실패 {r.stdout[-200:]}")
                continue
            res = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
            results[name] = res
            global name_is_long
            name_is_long = name == "long.txt"
            fails += [f"{name}: {x}" for x in compare(res, (fmt, n, speakers, first))]
        # 이어 붙인 줄, 시각, 긴 발언 분할
        sp = results.get("speaker.txt")
        if sp and "앞 발언에 붙습니다" not in sp["segments"][1]["text"]:
            fails.append("화자 표기 없는 줄이 앞 발언에 붙지 않았다")
        st = results.get("stamped.txt")
        if st and st["segments"][1]["start"] != 9:
            fails.append(f"시각 파싱 {st['segments'][1]['start']}")
        tm = results.get("teams.vtt")
        if tm and "Then budget" not in tm["segments"][0]["text"]:
            fails.append("같은 화자의 연속 자막이 합쳐지지 않았다")
        lg = results.get("long.txt")
        if lg and not all(s["speaker"] == "김민지" for s in lg["segments"][:-1]):
            fails.append("긴 발언을 나눈 조각의 화자가 유지되지 않았다")
        # 워드 입력
        from docx import Document
        d = Document()
        for line in ["김민지: 워드로 받은 회의록입니다.", "이준호: 네, 확인했습니다."]:
            d.add_paragraph(line)
        d.save(str(T / "minutes.docx"))
        r = run_script("prepare_transcript.py", T / "minutes.docx", "--out-dir", T / "docx_out")
        if "segments=2" not in r.stdout:
            fails.append(f"docx 입력 실패: {r.stdout[-200:]}")
        # 실습 녹취록(클로바노트 형식)
        r = run_script("prepare_transcript.py", TEXT, "--out-dir", T / "practice")
        res = json.loads((T / "practice" / "transcript.json").read_text(encoding="utf-8"))
        k = KEY["text"]
        if res["meta"]["format"] != "clova" or sorted(res["meta"]["speakers"]) != sorted(k["attendees"]) or len(res["segments"]) != 33:
            fails.append(f"실습 녹취록: {res['meta']['format']}, 화자 {res['meta']['speakers']}, 발언 {len(res['segments'])}")
        if not res["meta"]["header"] or "2026.03.09" not in res["meta"]["header"][1]:
            fails.append("클로바노트 머리글(날짜)을 보존하지 않았다")
        # 양성 대조: 틀린 기대값이면 비교가 실패해야 한다
        if sp and not compare(sp, ("speaker", 99, ["홍길동"], "없는 문장")):
            fails.append("양성 대조 실패: 틀린 기대값에도 비교가 통과했다")
        empty = T / "empty.txt"
        empty.write_text("\n\n", encoding="utf-8")
        r = run_script("prepare_transcript.py", empty, "--out-dir", T / "empty_out")
        if r.returncode == 0:
            fails.append("빈 파일을 오류로 처리하지 않았다")
    for f in fails:
        print("FAIL", f)
    if fails:
        print(f"PREPARE TRANSCRIPT FAILED ({len(fails)})")
        return 1
    print(f"PREPARE TRANSCRIPT OK — 형식 {len(CASES)}종 + 워드 + 실습 녹취록(클로바노트 33발언) 변환, 양성 대조 통과")
    return 0


name_is_long = False

if __name__ == "__main__":
    sys.exit(main())
