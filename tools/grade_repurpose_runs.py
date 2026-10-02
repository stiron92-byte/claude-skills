#!/usr/bin/env python3
"""content-repurpose 평가 실행 결과 채점 (skill-creator grading.json 형식).

객관 항목은 결과 텍스트를 정답표(answer_key.json)와 플랫폼 규칙으로 검사한다. 두 구성을 같은 기준으로 채점하려고
- 결과 파일은 이름이 아니라 확장자(.md·.txt)로 고르고, 원본 사본·브리프·중간 파일(원본·source·brief·.json)은 제외한다
- 플랫폼 섹션은 '## 제목'(없으면 '### 제목')에서 찾고, 제목 별칭은 count_chars.py와 같다
- 뉴스레터 제목·프리헤더는 '제목(subject line):'처럼 꾸민 라벨도 인정한다
글자 수·숫자 출처는 이 저장소의 count_chars·check_repurpose 규칙을 쓴다(객관 규칙이므로 두 구성에 같게 적용).
[판단] 항목은 judgments.json으로 채점자가 넣는다.

사용법: python tools/grade_repurpose_runs.py <iteration 디렉터리> [--judgments judgments.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/kevin-skills-creator/skills/content-repurpose/scripts"
INPUTS = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/content-repurpose/inputs"
KEY = json.loads((INPUTS / "answer_key.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(SCRIPTS))
from count_chars import HASHTAG, find_platform, measure, sections  # noqa: E402
from check_repurpose import verify  # noqa: E402

EXCLUDE = re.compile(r"(원본|source|brief|transcript|draft|초안)", re.I)
BLOGS = ("seo_blog", "naver_blog", "brunch", "medium")


def result_files(run: Path) -> list[Path]:
    return sorted(p for p in (run / "outputs").rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".txt")
                  and p.name != "final_response.md" and not EXCLUDE.search(p.name))


def final_text(run: Path) -> str:
    p = run / "outputs" / "final_response.md"
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def has(t: str, *alts) -> bool:
    return any(a.lower() in t.lower() for a in alts)


def platform_sections(md: str) -> dict[str, str]:
    """count_chars.sections와 같은 규칙(블로그 소제목은 본문으로). '##' 플랫폼 제목이 없으면 '###'로 다시 본다."""
    for text in (md, re.sub(r"^###\s", "## ", md, flags=re.M)):
        out: dict[str, str] = {}
        for head, body in sections(text):
            pid = find_platform(head)
            if pid:
                out.setdefault(pid, body)
        if out:
            return out
    return {}


def label(body: str, *names) -> str | None:
    m = re.search(r"^\s*[*_#>-]*\s*(?:" + "|".join(names) + r")[^:：\n]{0,25}[:：]\s*\**\s*(.+?)\s*\**\s*$", body, re.I | re.M)
    if m:
        return m.group(1).strip().strip("*").strip()
    # '**핀 제목**' 줄 다음 줄에 값을 쓴 형식
    lines = body.splitlines()
    for i, l in enumerate(lines):
        if re.fullmatch(r"\s*\*\*\s*(?:" + "|".join(names) + r")[^*\n]{0,25}\*\*\s*", l, re.I):
            nxt = next((x.strip() for x in lines[i + 1:] if x.strip()), None)
            if nxt and not nxt.startswith("**"):
                return nxt
    return None


def block_after(body: str, header_pat: str) -> str | None:
    """'**내레이션 전문**' 같은 굵은 제목 아래, 다음 굵은 제목 전까지의 글"""
    lines = body.splitlines()
    for i, l in enumerate(lines):
        if re.search(header_pat, l) and l.strip().startswith("**"):
            out = []
            for x in lines[i + 1:]:
                if x.strip().startswith("**") and x.strip().endswith("**"):
                    break
                out.append(x)
            return "\n".join(out)
    return None


def drop_tables(body: str) -> str:
    """소셜 게시글 안의 마크다운 표 줄(작성 메모·요약 표)은 게시 본문이 아니다"""
    return "\n".join(l for l in body.splitlines() if not l.strip().startswith("|"))


def grade(run: Path, meta: dict) -> list[dict]:
    A = meta["assertions"]
    name = meta["eval_name"]
    files = result_files(run)
    doc = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files)
    fin = final_text(run)
    both = doc + "\n" + fin
    units = [l for l in both.splitlines() if l.strip()]
    res: dict[str, tuple] = {t: (None, "판단 대기") for t in A if t.startswith("[판단]")}

    def put(i, ok, why):
        res[A[i]] = (bool(ok), why)

    if name == "audit-blog-list":
        put(0, len(both) > 800 and has(both, "AI 도구"), f"결과 파일 {[f.name for f in files]}, 응답 {len(fin)}자")
        top = any("AI 도구" in u and re.search(r"(?<!\d)5\s*(개|편|건)?\b|5개|50\s*%", u) for u in units)
        others = {c: any(c in u and re.search(r"(?<![\d.])1\s*(개|편|건)?(?![\d,%])|10\s*%", u) for u in units)
                  for c in ("AI 활용", "커리어", "AI 뉴스", "AI 전망", "AI 개념")}
        put(1, top and all(others.values()), f"AI 도구 5·50% {top}, 나머지 {others}")
        put(2, any("AI 도구" in u and has(u, "편중", "쏠림", "집중", "치우", "50%", "절반") for u in units), "AI 도구 편중 언급")
        gap = has(both, "18개월", "1년 반", "1년 넘", "1년 이상", "1년 6개월", "발행 공백", "발행이 멈", "발행 중단", "2025년 4월 이후", "2025.04 이후", "업데이트가 없")
        allold = any(re.search(r"(10개|10편|전부|모든|모두).{0,20}6개월", u) or re.search(r"6개월.{0,20}(10개|10편|전부|모든|모두)", u) for u in units)
        put(3, gap or allold, f"발행 공백 {gap}, 전체 6개월 경과 {allold}")
        ts = [t for t in ("GPT-4o", "Claude 3.5", "2025 AI 트렌드") if any(t in u and has(u, "업데이트", "갱신", "최신", "개정", "리프레시", "리뉴얼", "보완", "다시") for u in units)]
        put(4, len(ts) >= 2, f"업데이트 지목 {ts}")
        put(5, has(both, "즉시", "1주") and has(both, "단기", "1개월", "한 달") and has(both, "중기", "3개월", "분기"), "우선순위별 액션 플랜")
    elif name == "gap-competitor":
        put(0, len(both) > 800, f"결과 파일 {[f.name for f in files]}, 응답 {len(fin)}자")
        put(1, has(both, "생략", "일부 목록", "일부만", "부분 목록", "전체 목록이 아", "전체 목록을 받", "목록 전체", "제한적"), "일부 목록 기준 표시")
        g = [k for k, ws in {"실전": ("부동산", "실전 활용", "도메인"), "자동화": ("비개발자", "자동화 워크플로", "노코드", "자동화"),
                              "뉴스레터": ("뉴스레터 자동", "뉴스레터")}.items() if has(doc or fin, *ws)]
        put(2, len(g) >= 2, f"주제 갭 {g}")
        put(3, has(both, "실습형", "튜토리얼", "따라하기", "핸즈온"), "형식 갭")
        put(4, (has(both, "1주차", "1주 차", "Week 1", "W1") and has(both, "4주차", "4주 차", "Week 4", "W4")) or bool(re.search(r"\|\s*(1|4)\s*주", both)), "4주 로드맵")
    else:
        src = (run / "work" / "원본_유튜브대본_뉴스레터1000명.md").read_text(encoding="utf-8")
        secs = platform_sections(doc)
        for k in ("x_thread", "threads", "instagram", "linkedin", "facebook"):
            if k in secs:
                secs[k] = drop_tables(secs[k])
        joined = "\n".join(f"## {pid_name(k)}\n{v}" for k, v in secs.items())
        issues, warns, rows = verify(joined, src, [], None)
        prov = [i["detail"] for i in issues if i["check"] == "number-provenance"]
        form = [f"{i['check']}:{i['detail'][:30]}" for i in issues if i["check"] in ("placeholder", "meta-label", "code-fence", "preamble")]
        if name == "repurpose-blog-x-instagram":
            blog = next((secs[b] for b in BLOGS if b in secs), None)
            put(0, blog is not None and "x_thread" in secs and "instagram" in secs, f"섹션 {sorted(secs)}")
            if "x_thread" in secs:
                r = measure("x_thread", secs["x_thread"])
                put(1, r["tweets"] > 0 and max(r["tweet_weights"]) <= 280, f"트윗 {r['tweets']}개, 최대 가중치 {max(r['tweet_weights'] or [0])}")
            else:
                put(1, False, "X 스레드 없음")
            if "instagram" in secs:
                body = secs["instagram"].strip()
                ht = len(HASHTAG.findall(body))
                put(2, len(body) <= 2200 and ht <= 30, f"{len(body)}자, 해시태그 {ht}개")
            else:
                put(2, False, "인스타 없음")
            put(3, bool(secs) and not prov, f"원본에 없는 숫자 {prov[:6]}" if prov else "없음")
            put(4, bool(secs) and not form, f"형식 문제 {form[:5]}" if form else "없음")
            cm = [c["key"] for c in KEY["repurpose"]["core_messages"] if blog and has(blog, *c["any"])]
            put(5, len(cm) == 3, f"블로그 핵심 메시지 {cm}")
            put(6, bool(blog) and has(blog, "유료화", "분야마다", "사람마다", "제 경우", "개인차", "다를 수"), "블로그 단서")
        elif name == "repurpose-short-platforms":
            sh, th, pi = secs.get("yt_shorts") or secs.get("tiktok"), secs.get("threads"), secs.get("pinterest")
            put(0, sh is not None and th is not None and pi is not None, f"섹션 {sorted(secs)}")
            put(1, th is not None and len(th.strip()) <= 500, f"Threads {len(th.strip()) if th else '없음'}자")
            if pi is not None:
                title = label(pi, "핀 제목", "제목", "title") or ""
                desc = label(pi, "설명", "핀 설명", "description")
                if desc is None:
                    desc = "\n".join(l for l in pi.splitlines() if l.strip() and not re.match(r"^\s*[*_]*\s*(핀 제목|제목|보드|board|title|키워드)", l, re.I))
                put(2, 0 < len(title) <= 100 and len(desc.strip()) <= 500, f"제목 {len(title)}자, 설명 {len(desc.strip())}자")
            else:
                put(2, False, "Pinterest 없음")
            if sh is not None:
                spoken = []
                full = block_after(sh, r"(내레이션|대사|나레이션)\s*(전문|만|전체)")
                for l in (full if full is not None else sh).splitlines():
                    if not l.strip() or re.search(r"(자막|화면|컷|장면|b-roll|bgm|효과음|연출|텍스트|썸네일|촬영|편집|제목|길이|분량)\s*[:：]?", l, re.I) and not re.search(r"(대사|내레이션|나레이션|음성)\s*[:：]", l):
                        continue
                    l = re.sub(r"\([^)]*\)|\[[^\]]*\]|（[^）]*）", "", l)
                    l = re.sub(r"^\s*[*_>#|-]*\s*(대사|내레이션|나레이션|음성|\d+\s*[~-]\s*\d+\s*초)\s*[:：]?", "", l)
                    spoken.append(l.strip())
                n = len("".join(spoken))
                put(3, 0 < n <= 400, f"대사 {n}자")
            else:
                put(3, False, "쇼츠 대본 없음")
            put(4, bool(secs) and not prov, f"원본에 없는 숫자 {prov[:6]}" if prov else "없음")
            put(5, bool(secs) and not form, f"형식 문제 {form[:5]}" if form else "없음")
        elif name == "repurpose-english-x-thread":
            x = secs.get("x_thread")
            letters = re.findall(r"[A-Za-z가-힣]", x or "")
            en = sum(1 for c in letters if c.isascii()) / max(len(letters), 1)
            put(0, x is not None and en >= 0.8, f"X 스레드 {'있음' if x else '없음'}, 영문 비율 {en:.0%}")
            if x is not None:
                r = measure("x_thread", x)
                put(1, r["tweets"] > 0 and max(r["tweet_weights"]) <= 280, f"트윗 {r['tweets']}개, 최대 가중치 {max(r['tweet_weights'] or [0])}")
                put(2, 5 <= r["tweets"] <= 10, f"트윗 {r['tweets']}개")
            else:
                put(1, False, "X 없음")
                put(2, False, "X 없음")
            put(3, bool(secs) and not prov, f"원본에 없는 숫자 {prov[:6]}" if prov else "없음")
            put(4, bool(secs) and not form, f"형식 문제 {form[:5]}" if form else "없음")
        else:
            li, nl = secs.get("linkedin"), secs.get("newsletter")
            put(0, li is not None and nl is not None, f"섹션 {sorted(secs)}")
            if li is not None:
                body = li.strip()
                ht = len(HASHTAG.findall(body))
                put(1, len(body) <= 1300, f"{len(body)}자")
                put(2, 3 <= ht <= 5, f"해시태그 {ht}개")
            else:
                put(1, False, "LinkedIn 없음")
                put(2, False, "LinkedIn 없음")
            subj = label(nl or "", "제목", "subject", "메일 제목", "이메일 제목")
            pre = label(nl or "", "프리헤더", "preheader", "미리보기")
            put(3, bool(subj) and len(subj) <= 50, f"제목 {subj!r} {len(subj) if subj else 0}자")
            put(4, bool(pre) and len(pre) <= 80, f"프리헤더 {pre!r} {len(pre) if pre else 0}자")
            put(5, bool(secs) and not prov, f"원본에 없는 숫자 {prov[:6]}" if prov else "없음")
            put(6, bool(secs) and not form, f"형식 문제 {form[:5]}" if form else "없음")
    (run / "_grade").mkdir(exist_ok=True)
    (run / "_grade" / "result_text.md").write_text(doc + "\n\n## 최종 응답(채점 참고)\n" + fin, encoding="utf-8")
    return [{"text": t, "passed": res.get(t, (False, "채점 규칙 없음"))[0], "evidence": res.get(t, (False, "채점 규칙 없음"))[1]} for t in A]


NAMES = {"seo_blog": "SEO 블로그 포스트", "naver_blog": "네이버 블로그", "brunch": "브런치 글", "medium": "Medium 아티클", "x_thread": "X 스레드",
         "linkedin": "LinkedIn 게시물", "instagram": "Instagram 캡션", "threads": "Threads 게시물", "facebook": "Facebook 게시물",
         "newsletter": "뉴스레터", "yt_shorts": "YouTube Shorts 스크립트", "tiktok": "TikTok 스크립트", "pinterest": "Pinterest 핀",
         "thumbnail": "썸네일·비주얼 가이드"}


def pid_name(pid: str) -> str:
    return NAMES.get(pid, pid)


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("iteration")
    ap.add_argument("--judgments")
    a = ap.parse_args(argv)
    it = Path(a.iteration)
    judg = json.loads(Path(a.judgments).read_text(encoding="utf-8")) if a.judgments else {}
    pending = 0
    for meta_file in sorted(it.glob("eval-*/eval_metadata.json")):
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        for cfg_dir in sorted(p for p in meta_file.parent.iterdir() if p.is_dir()):
            for run_dir in sorted(cfg_dir.glob("run-*")):
                key = f"{meta['eval_name']}/{cfg_dir.name}"
                exps = grade(run_dir, meta)
                for x in exps:
                    j = judg.get(key, {}).get(x["text"])
                    if j:
                        x["passed"], x["evidence"] = bool(j["passed"]), j["evidence"]
                passed = sum(1 for x in exps if x["passed"] is True)
                decided = sum(1 for x in exps if x["passed"] is not None)
                pending += len(exps) - decided
                (run_dir / "grading.json").write_text(json.dumps({"expectations": exps, "summary": {
                    "passed": passed, "failed": decided - passed, "total": len(exps),
                    "pass_rate": round(passed / len(exps), 4) if exps else 0}}, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"{key:<45} {passed}/{len(exps)}  (판단 대기 {len(exps) - decided})")
    print(f"PENDING JUDGMENTS {pending}" if pending else "GRADED ALL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
