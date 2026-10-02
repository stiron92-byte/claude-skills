#!/usr/bin/env python3
"""리퍼포징 결과 품질 게이트 — 사용자에게 전달하기 전에 반드시 통과시킨다.

결과 파일은 플랫폼마다 '## 플랫폼명' 섹션 하나(count_chars.py와 같은 규칙)로 쓴다.

오류(전달 금지)
- missing-platform: 요청한 플랫폼 섹션이 없다(--platforms)
- limit: 플랫폼이 실제로 막는 한도를 넘었다(X 트윗 가중치 280, 인스타 2,200자·해시태그 30개, Threads 500자 등)
- required: 플랫폼 필수 요소가 없다(SEO 블로그 제목·메타 디스크립션 줄, 뉴스레터 제목 줄)
- placeholder: [링크]·[여기에 입력]·TODO·○○ 같은 미완성 표시(네이버 블로그·브런치의 [이미지 제안: …]은 허용)
- meta-label: "톤:", "형식:", "필수 요소:" 같은 작성용 메모가 결과물에 남았다
- code-fence: 결과를 코드 블록(```)으로 감쌌다(붙여 넣으면 기호가 그대로 보인다)
- preamble: "아래는 ~입니다" 같은 안내 문장으로 섹션이 시작한다
- number-provenance: 결과의 숫자가 원본(--source)에 없다(단위 표기 차이는 허용. 단위 없는 9 이하 정수·트윗 번호·목록 번호·이미지 규격(1080x1350, 4:5) 제외)
- core-message-missing: brief.json의 핵심 메시지를 하나도 담지 않은 플랫폼(--brief)
경고
- 권장 분량·해시태그 수·트윗 수를 벗어남, 핵심 메시지 일부 누락

사용법
  python check_repurpose.py <결과.md> --source <원본 파일> [--platforms x_thread,instagram,seo_blog] [--brief brief.json] [--json]
  brief.json: {"core_messages": [{"text": "주제를 좁힌다", "keywords": ["좁", "함수 하나"]}, …]}
마지막 줄: REPURPOSE VERIFY OK 또는 REPURPOSE VERIFY FAILED
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_chars import PLATFORMS, find_platform, measure, sections  # noqa: E402

PLACEHOLDER = re.compile(r"(\[(?:여기|링크|URL|url|이미지|사진|입력|작성|브랜드|회사명|이름)[^\]]{0,30}\]|\bTODO\b|\bTBD\b|XXX|○○|\{\{[^}]*\}\}|<여기[^>]*>)")
IMAGE_SUGGEST = re.compile(r"\[이미지 제안[:：][^\]]+\]")
META = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?(톤|형식|필수 요소|필수 구조|구조|글자 ?수|분량|타깃|목적|플랫폼 특성|작성 의도)(?:\*\*)?\s*[:：]", re.M)
PREAMBLE = re.compile(r"^\s*(아래는|다음은|다음과 같이|요청하신|이 글은 .{0,20}(변환|작성)|변환한 결과|Here is|Below is)")
NUM = re.compile(r"(?<![A-Za-z0-9.#])[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![0-9])|(?<![A-Za-z0-9.,#])[-+]?\d+(?:\.\d+)?")
UNIT = re.compile(r"\s?(조|억|천만|백만|만|천)")
UNIT_MULT = {"조": 1e12, "억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "천": 1e3}
LINE_MARKERS = re.compile(r"^\s*(?:\*\*)?(\d{1,2}\s*/\s*\d{1,2}|\d{1,2}[.)])(?:\*\*)?\s", re.M)
HASHTAG_OR_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[^\s#]+")


# 9 이하 정수도 측정 단위가 붙으면 검사한다("2시간", "0%"는 지어내기 쉬운 숫자다). "3가지", "2번째"는 검사하지 않는다
MEASURE = re.compile(r"\s?(시간|분|초|%|퍼센트|명|원|개월|달|년|주|일|배|회|건|살|세|kg|km|GB|MB|위)")


DIMENSION = re.compile(r"\b\d{2,5}\s*[x×X]\s*\d{2,5}\b(?:\s*px)?|\b\d{1,2}\s*:\s*\d{1,2}\b(?!\s*\d)")  # 1080x1350, 16:9 같은 이미지 규격


TIMECUE = re.compile(r"\d{1,3}\s*[~\-–]\s*\d{1,3}\s*초|(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?!\d)")  # 쇼츠 대본 시간 표시 (0~3초), 00:15


def numbers(text: str) -> list[tuple[str, float, str | None]]:
    """(토큰, 단위 배수, 측정 단위 또는 None)"""
    t = DIMENSION.sub(" ", text)
    t = TIMECUE.sub(" ", t)
    t = LINE_MARKERS.sub(" ", t)
    t = HASHTAG_OR_HEX.sub(" ", t)
    out = []
    for m in NUM.finditer(t):
        u = UNIT.match(t, m.end())
        mu = MEASURE.match(t, m.end())
        out.append((m.group(0), UNIT_MULT[u.group(1)] if u else 1.0, mu.group(1) if mu else None))
    return out


def value(tok: str) -> float | None:
    try:
        return float(tok.replace(",", "").replace("+", ""))
    except ValueError:
        return None


def source_values(src: str) -> set[float]:
    vals = set()
    for tok, mult, _ in numbers(src):
        v = value(tok)
        if v is not None:
            vals.add(round(v, 4))
            vals.add(round(v * mult, 4))
    return vals


def verify(md: str, src: str | None, want: list[str], brief: dict | None) -> tuple[list, list, list]:
    issues, warns, rows = [], [], []
    secs = [(h, b, find_platform(h)) for h, b in sections(md)]
    found = {pid for _, _, pid in secs if pid}
    for w in want:
        if w not in found:
            issues.append({"check": "missing-platform", "where": w, "detail": f"요청한 플랫폼 '{PLATFORMS.get(w, {}).get('name', w)}' 섹션이 없다"})
    svals = source_values(src) if src else None
    for head, body, pid in secs:
        if not pid:
            continue
        r = measure(pid, body)
        rows.append({"heading": head, **{k: v for k, v in r.items() if k != "labels"}})
        for p in r["problems"]:
            issues.append({"check": "required" if "없다" in p else "limit", "where": head, "detail": p})
        for n in r["notes"]:
            warns.append({"check": "guide", "where": head, "detail": n})
        scan = IMAGE_SUGGEST.sub(" ", body) if pid in ("naver_blog", "brunch") else body
        for m in PLACEHOLDER.finditer(scan):
            issues.append({"check": "placeholder", "where": head, "detail": m.group(0)})
        for m in META.finditer(body):
            issues.append({"check": "meta-label", "where": head, "detail": m.group(0).strip()})
        if "```" in body:
            issues.append({"check": "code-fence", "where": head, "detail": "코드 블록 기호(```)"})
        first = next((l for l in body.splitlines() if l.strip()), "")
        if PREAMBLE.match(first):
            issues.append({"check": "preamble", "where": head, "detail": first[:50]})
        if svals is not None:
            flat_src = re.sub(r"\s+", "", src)
            for tok, mult, unit in numbers(body):
                v = value(tok)
                small = v is not None and v.is_integer() and abs(v) <= 9 and "." not in tok and mult == 1.0  # 1천·2만은 값으로 대조
                if v is None or (small and not unit):
                    continue
                if small:  # 작은 수는 값만으로는 우연히 맞기 쉽다(2시간 ↔ 2만원) → 숫자+단위가 원본에 있어야 한다
                    if tok + unit not in flat_src:
                        issues.append({"check": "number-provenance", "where": head, "detail": f"'{tok}{unit}'이(가) 원본에 없다"})
                    continue
                if not ({round(v, 4), round(v * mult, 4)} & svals):
                    issues.append({"check": "number-provenance", "where": head, "detail": f"'{tok}'이(가) 원본에 없다"})
        if brief and brief.get("core_messages"):
            low = body.lower()
            hit = [c["text"] for c in brief["core_messages"] if any(k.lower() in low for k in c.get("keywords", [c["text"]]))]
            miss = [c["text"] for c in brief["core_messages"] if c["text"] not in hit]
            if not hit and pid not in ("thumbnail", "pinterest"):
                issues.append({"check": "core-message-missing", "where": head, "detail": "핵심 메시지를 하나도 담지 않았다"})
            elif miss and pid in ("seo_blog", "naver_blog", "brunch", "medium", "newsletter", "linkedin", "x_thread"):
                warns.append({"check": "core-message-partial", "where": head, "detail": f"빠진 핵심 메시지: {miss}"})
    return issues, warns, rows


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="리퍼포징 결과 품질 게이트")
    ap.add_argument("result")
    ap.add_argument("--source")
    ap.add_argument("--platforms", default="")
    ap.add_argument("--brief")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    md = Path(a.result).read_text(encoding="utf-8")
    src = Path(a.source).read_text(encoding="utf-8") if a.source else None
    want = []
    for w in [x.strip() for x in a.platforms.split(",") if x.strip()]:
        want.append(w if w in PLATFORMS else (find_platform(w) or w))
    brief = json.loads(Path(a.brief).read_text(encoding="utf-8")) if a.brief else None
    issues, warns, rows = verify(md, src, want, brief)
    if not src:
        warns.append({"check": "no-source", "detail": "원본(--source)이 없어 숫자 출처를 검사하지 않았다"})
    if a.json:
        print(json.dumps({"errors": issues, "warnings": warns, "platforms": rows}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            extra = f", 트윗 {r['tweets']}개" if r["platform"] == "x_thread" else ""
            print(f"[{r['heading']}] {r['chars']}자, 해시태그 {r['hashtags']}개{extra}")
        for i in issues:
            print(f"ERROR [{i['check']}] {i.get('where', '')} {i['detail']}")
        for w in warns:
            print(f"WARN  [{w['check']}] {w.get('where', '')} {w['detail']}")
    print(f"REPURPOSE VERIFY {'OK' if not issues else 'FAILED'} platforms={len(rows)} errors={len(issues)} warnings={len(warns)}")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
