#!/usr/bin/env python3
"""M5: verify_minutes.py가 회의록 결함을 각각 잡아내는지 양성 대조로 확인한다.

먼저 기준 회의록(정답)이 통과하는지 보고, 그다음 결함을 하나씩 넣은 사본마다 해당 검사 이름이 오류로 나와야 한다.
허용해야 하는 표현(만 단위 표기, 요일에 맞는 계산 날짜, 선언한 STT 교정)은 통과해야 한다.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _meeting_fixtures import GOOD_MINUTES, TEXT, run_script  # noqa: E402

results: list[tuple[str, bool, str]] = []


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        T = Path(td)
        run_script("prepare_transcript.py", TEXT, "--out-dir", T)
        tr = T / "transcript.json"

        def verify(m: dict, rendered: list[Path] | None = None, transcript: Path = tr) -> dict:
            p = T / "m.json"
            p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            r = run_script("verify_minutes.py", p, "--transcript", transcript, "--json", *(["--rendered", *rendered] if rendered else []))
            try:
                return json.loads(r.stdout[: r.stdout.rindex("MINUTES VERIFY")])
            except ValueError:
                return {"errors": [{"check": "crashed", "detail": r.stdout[-300:] + r.stderr[-300:]}], "warnings": []}

        def expect(name, fn, check, rendered=None):
            m = copy.deepcopy(GOOD_MINUTES)
            fn(m)
            got = {e["check"] for e in verify(m, rendered)["errors"]}
            results.append((name, check in got, f"기대 {check}, 실제 {sorted(got)}"))

        def expect_ok(name, fn=lambda m: None, rendered=None):
            m = copy.deepcopy(GOOD_MINUTES)
            fn(m)
            errs = verify(m, rendered)["errors"]
            results.append((name, not errs, f"오류 {[e['check'] + ':' + e.get('detail', '')[:50] for e in errs]}"))

        expect_ok("기준 회의록 통과")
        expect_ok("만 단위·원 표기 허용", lambda m: m["summary"].append("예산 총 4,500만 원 중 검색광고가 2천만 원이다."))
        expect_ok("요일에 맞는 계산 날짜 허용", lambda m: m["action_items"][0].update(due="수요일(3월 11일)"))
        expect_ok("선언한 STT 교정 허용", lambda m: (m["meta"]["corrections"].append({"heard": "준호 님", "corrected": "준호PM", "evidence": ["T0001"]}),
                                                 m["action_items"][0].update(owner="준호PM")))
        expect("근거 없는 결정", lambda m: m["decisions"][0].pop("evidence"), "evidence-missing")
        expect("없는 발언 번호", lambda m: m["decisions"][1].update(evidence=["T0999"]), "evidence-unknown")
        expect("지어낸 숫자", lambda m: m["summary"].append("예산은 총 5,200만 원이다."), "number-provenance")
        expect("지어낸 비율", lambda m: m["agenda"][1]["points"].append("목표 전환율 4.2%"), "number-provenance")
        expect("녹취에 없는 담당자", lambda m: m["action_items"][3].update(owner="홍길동"), "owner-unsupported")
        expect("근거 없는 기한", lambda m: m["action_items"][0].update(due="목요일"), "due-unsupported")
        expect("근거 없는 상대 기한", lambda m: m["action_items"][3].update(due="내일"), "due-unsupported")
        expect("요일과 안 맞는 날짜", lambda m: m["action_items"][0].update(due="수요일(3/12)"), "due-date-mismatch")
        expect("녹취에 없는 참석자", lambda m: m["meta"]["attendees"].append("홍길동"), "attendee-unsupported")
        expect("근거 없는 STT 교정", lambda m: m["meta"]["corrections"].append({"heard": "김 피암", "corrected": "김PM", "evidence": ["T0001"]}),
               "correction-unsupported")
        expect("홍보 문구", lambda m: m["summary"].append("이 스킬은 강의 노트 정리, 인터뷰 기록에도 쓸 수 있습니다."), "promo-text")
        expect("추가 섹션의 지어낸 숫자", lambda m: m["sections"][0]["items"].append("반품률 7.5% 증가 우려"), "number-provenance")
        expect("필수 키 없음", lambda m: m.pop("action_items"), "schema")
        expect("다음 회의 근거 없음", lambda m: m["next_meeting"].pop("evidence"), "evidence-missing")
        # 렌더링 결과 대조
        m = copy.deepcopy(GOOD_MINUTES)
        mp = T / "good.json"
        mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        full = T / "full.md"
        run_script("build_minutes.py", mp, "--out", full, "--purpose", "team", "--transcript", tr)
        expect_ok("렌더링 문서 전체 포함", rendered=[full])
        cut = T / "cut.md"
        cut.write_text("\n".join(l for l in full.read_text(encoding="utf-8").splitlines() if "챗봇 시나리오" not in l), encoding="utf-8")
        expect("렌더링에서 할 일 누락", lambda m: None, "rendered-missing", rendered=[cut])
        left = T / "left.md"
        left.write_text(full.read_text(encoding="utf-8") + "\n- TODO 담당자 확인\n", encoding="utf-8")
        expect("자리표시 남음", lambda m: None, "leftover", rendered=[left])
        promo = T / "promo.md"
        promo.write_text(full.read_text(encoding="utf-8") + "\n💡 이 스킬은 회의록 외에도 활용할 수 있어요\n", encoding="utf-8")
        expect("문서 끝 홍보 문구", lambda m: None, "promo-text", rendered=[promo])
        # STT 확신 낮은 발언을 근거로 쓰면 경고
        t2 = json.loads(tr.read_text(encoding="utf-8"))
        t2["segments"][7]["low_confidence"] = True
        lowp = T / "low.json"
        lowp.write_text(json.dumps(t2, ensure_ascii=False), encoding="utf-8")
        w = {x["check"] for x in verify(copy.deepcopy(GOOD_MINUTES), transcript=lowp)["warnings"]}
        results.append(("확신 낮은 근거 경고", "low-confidence-evidence" in w, f"경고 {sorted(w)}"))
    bad = [r for r in results if not r[1]]
    for name, ok, why in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f" — {why}"))
    if bad:
        print(f"VERIFY MINUTES CONTROL FAILED ({len(bad)}/{len(results)})")
        return 1
    n_ok = sum(1 for n, _, _ in results if n.endswith(("통과", "허용", "포함")))
    print(f"VERIFY MINUTES CONTROL OK — 허용 사례 {n_ok}종 통과, 결함 {len(results) - n_ok}종 모두 검출")
    return 0


if __name__ == "__main__":
    sys.exit(main())
