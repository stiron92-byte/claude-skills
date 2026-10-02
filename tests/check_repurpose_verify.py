#!/usr/bin/env python3
"""R3: check_repurpose.py가 리퍼포징 결과의 결함을 각각 잡아내는지 양성 대조로 확인한다.

기준 결과물(정답)이 통과하는지 먼저 보고, 결함을 하나씩 넣은 사본마다 해당 검사 이름이 오류로 나와야 한다.
허용해야 하는 표현(만 단위 표기, 트윗 번호, 네이버 블로그 이미지 제안, HEX 색상)은 통과해야 한다.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repurpose_fixtures import BRIEF, GOOD, ROOT, SKILL, SOURCE, run_script  # noqa: E402

results: list[tuple[str, bool, str]] = []
PLATS = "x_thread,instagram,seo_blog"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        T = Path(td)
        brief = T / "brief.json"
        brief.write_text(json.dumps(BRIEF, ensure_ascii=False), encoding="utf-8")

        def verify(md: str, plats: str = PLATS) -> dict:
            p = T / "r.md"
            p.write_text(md, encoding="utf-8")
            r = run_script("check_repurpose.py", p, "--source", SOURCE, "--platforms", plats, "--brief", brief, "--json")
            try:
                return json.loads(r.stdout[: r.stdout.rindex("REPURPOSE VERIFY")])
            except ValueError:
                return {"errors": [{"check": "crashed", "detail": r.stdout[-300:] + r.stderr[-300:]}], "warnings": []}

        def expect(name, md, check, plats=PLATS):
            got = {e["check"] for e in verify(md, plats)["errors"]}
            results.append((name, check in got, f"기대 {check}, 실제 {sorted(got)}"))

        def expect_ok(name, md, plats=PLATS):
            errs = verify(md, plats)["errors"]
            results.append((name, not errs, f"오류 {[e['check'] + ':' + e.get('detail', '')[:50] for e in errs]}"))

        expect_ok("기준 결과물 통과", GOOD)
        expect_ok("만 단위 표기 허용", GOOD.replace("구독자 1,000명을 모았습니다", "구독자 천 명(1천 명)을 모았습니다"))
        naver = GOOD + "\n## 네이버 블로그\n\n안녕하세요! 오늘은 뉴스레터 이야기예요.\n\n[이미지 제안: 화요일 아침 출근길 지하철]\n\n주제를 좁히고 화요일 오전 7시에 보냈더니 구독자가 1,000명이 됐어요.\n"
        expect_ok("네이버 블로그 이미지 제안 허용", naver, PLATS + ",naver_blog")
        thumb = GOOD + "\n## 썸네일·비주얼 가이드\n\n썸네일 텍스트: 퇴근 후 1시간\n주 색상 #1E3A5F, 강조 #FFC93C\n"
        expect_ok("HEX 색상 허용", thumb, PLATS + ",thumbnail")

        shorts = GOOD + "\n## YouTube Shorts 스크립트\n\n(0~3초) 퇴근 후 1시간, 구독자 1,000명.\n화면 자막: 87명 → 1,000명\n(3~20초) 주제를 좁히고 화요일 오전 7시에 보냈어요.\n"
        expect_ok("쇼츠 시간 표시 허용", shorts, PLATS + ",yt_shorts")
        expect("요청한 플랫폼 누락", GOOD, "missing-platform", PLATS + ",linkedin")
        long_tweet = GOOD.replace("3/6 둘째, 발행 시간을 고정했습니다.", "3/6 둘째, 발행 시간을 고정했습니다." + " 정말 중요했어요" * 20)
        expect("트윗 280 초과", long_tweet, "limit")
        expect("지어낸 숫자", GOOD.replace("답장률 12%.", "답장률 12%, 공유율 35%."), "number-provenance")
        expect("지어낸 작은 숫자(단위 있음)", GOOD.replace("아직 유료화는 안 했고,", "하루 2시간이면 충분하고,"), "number-provenance")
        expect("지어낸 금액", GOOD.replace("아직 유료화는 안 했고,", "광고 수익 월 150만 원,"), "number-provenance")
        expect("자리표시", GOOD.replace("제목 짓는 법부터 풀어볼게요.", "제목 짓는 법부터 풀어볼게요. [링크]"), "placeholder")
        expect("TODO 남음", GOOD.replace("## Instagram 캡션\n", "## Instagram 캡션\nTODO 이미지 확정\n"), "placeholder")
        expect("메타 레이블", GOOD.replace("## Instagram 캡션\n", "## Instagram 캡션\n톤: 친근하고 감성적\n"), "meta-label")
        expect("코드 블록", GOOD.replace("## Instagram 캡션\n", "## Instagram 캡션\n```\n") + "```\n", "code-fence")
        expect("서두 안내 문구", GOOD.replace("## Instagram 캡션\n\n퇴근 후", "## Instagram 캡션\n\n아래는 인스타그램용 캡션입니다.\n퇴근 후"), "preamble")
        expect("SEO 메타 디스크립션 없음", "\n".join(l for l in GOOD.splitlines() if not l.startswith("메타 디스크립션")), "required")
        many = GOOD.replace("#직장인공부", "#직장인공부 " + " ".join(f"#추가{i}" for i in range(10)))
        expect("인스타 해시태그 30개 초과", many, "limit")
        off_inst = "## Instagram 캡션\n\n오늘은 날씨가 좋아요. 산책하기 좋은 날입니다.\n#산책 #날씨\n"
        expect("핵심 메시지 없는 플랫폼", GOOD.split("## Instagram 캡션")[0] + off_inst + "## SEO 블로그 포스트" + GOOD.split("## SEO 블로그 포스트")[1], "core-message-missing")
        nl = GOOD + "\n## 뉴스레터\n\n안녕하세요, 이번 호 소식입니다.\n주제를 좁히고 화요일 오전 7시에 보냈습니다.\n"
        expect("뉴스레터 제목 줄 없음", nl, "required", PLATS + ",newsletter")
        # 스킬 예시 파일 자체가 검증을 통과하는가(v2), v1.6.1 예시의 지어낸 숫자를 잡는가
        ex_dir = SKILL / "examples"
        ex_src = ex_dir / "source-1인개발자.md"
        r = run_script("check_repurpose.py", ex_dir / "example-usage.md", "--source", ex_src, "--platforms", "seo_blog,x_thread,instagram")
        results.append(("v2 스킬 예시 통과", "REPURPOSE VERIFY OK" in r.stdout, r.stdout[-300:]))
        old = subprocess.run(["git", "show", "v1.6.1:skills/content-repurpose/examples/example-usage.md"], capture_output=True,
                             cwd=ROOT, encoding="utf-8", errors="replace")
        if old.returncode == 0:
            body = old.stdout.split("## 변환 결과", 1)[-1].split("## 요약 표", 1)[0].replace("\n### ", "\n## ")
            (T / "v1.md").write_text(body, encoding="utf-8")
            r = run_script("check_repurpose.py", T / "v1.md", "--source", ex_src, "--json")
            got = json.loads(r.stdout[: r.stdout.rindex("REPURPOSE VERIFY")])
            toks = sorted({e["detail"].split("'")[1] for e in got["errors"] if e["check"] == "number-provenance"})
            results.append(("v1.6.1 예시의 지어낸 숫자 검출", {"30", "0%", "2시간", "4시간"} <= set(toks), f"검출 {toks}"))
        else:
            results.append(("v1.6.1 예시의 지어낸 숫자 검출", False, "git show 실패(태그 없음)"))
    bad = [r for r in results if not r[1]]
    for name, ok, why in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f" — {why}"))
    if bad:
        print(f"REPURPOSE VERIFY CONTROL FAILED ({len(bad)}/{len(results)})")
        return 1
    n_ok = sum(1 for n, _, _ in results if n.endswith(("통과", "허용")))
    print(f"REPURPOSE VERIFY CONTROL OK — 허용 사례 {n_ok}종 통과, 결함 {len(results) - n_ok}종 모두 검출")
    return 0


if __name__ == "__main__":
    sys.exit(main())
