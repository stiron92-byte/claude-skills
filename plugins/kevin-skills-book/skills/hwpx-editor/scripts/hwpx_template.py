#!/usr/bin/env python3
"""HWPX 양식 보존 텍스트 치환 엔진.

한글(HWPX) 문서의 양식(레이아웃, 로고, 결재란, 서체, 표 구조)은 그대로 두고 글자만 바꾼다.

설계 원칙
1. XML 파서로 다시 쓰지 않는다. ElementTree 등은 네임스페이스 접두사(hp:, hs: …)를 ns0 등으로
   바꿔 써서 한컴오피스가 파일을 열지 못한다. 문자열 단위로만 고친다.
2. 치환은 본문 텍스트 노드(<hp:t>…</hp:t>) 안에서만 한다. 태그 이름·속성값은 건드리지 않는다.
3. 새 텍스트는 XML 이스케이프한다(&, <, >). 이스케이프하지 않으면 문서가 깨진다.
4. 바꾸지 않은 ZIP 엔트리는 내용·순서·압축 방식을 그대로 복사한다. mimetype은 첫 엔트리·무압축을 유지한다.
5. 고친 XML에서만 linesegarray(줄 배치 캐시)를 지운다. 한컴오피스가 열 때 다시 계산한다.
   지우지 않으면 글자 길이가 바뀐 줄에서 글자가 겹쳐 보인다.
6. 계획 → 검증 → 실행: plan으로 모든 치환 대상이 정확히 몇 번 나오는지 먼저 확인한다.
   찾지 못한 대상이 있으면 기본적으로 실행하지 않는다(strict).

책 2장 예제와 같은 API(replace_texts, fill_template, extract_texts, scan_placeholders)를 유지한다.
외부 의존성 없음(stdlib만 사용).

CLI
  python hwpx_template.py extract 원본.hwpx [--paragraphs]
  python hwpx_template.py plan 원본.hwpx --map map.json
  python hwpx_template.py replace 원본.hwpx --map map.json --output 결과.hwpx [--allow-missing]
  python hwpx_template.py scan 양식.hwpx
  python hwpx_template.py fill 양식.hwpx --data data.json --output 결과.hwpx
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

DEFAULT_PATTERN = r"\{\{(\w+)\}\}"
LINESEG_PATTERN = re.compile(r"<(\w+:)?linesegarray\b[^>]*>.*?</(\w+:)?linesegarray>|<(\w+:)?linesegarray\b[^>]*/>", re.DOTALL)
# <hp:t> 또는 <hp:t attr="..."> … </hp:t>  (접두사가 hp가 아닌 문서도 있어 접두사는 일반화)
TEXT_NODE = re.compile(r"(<(?P<p>\w+):t(?:\s[^>]*)?>)(?P<body>.*?)(</(?P=p):t>)", re.DOTALL)
PARAGRAPH = re.compile(r"<(?P<p>\w+):p\b[^>]*>.*?</(?P=p):p>", re.DOTALL)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _unescape(text: str) -> str:
    return (text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&apos;", "'").replace("&amp;", "&"))


def _visible(body: str) -> str:
    """텍스트 노드 본문에서 하위 태그(탭·줄바꿈 등)를 뺀 보이는 글자."""
    return _unescape(re.sub(r"<[^>]+>", "", body))


def _check_hwpx(path: str | Path) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {p}")
    if not zipfile.is_zipfile(p):
        raise ValueError(f"HWPX(ZIP) 파일이 아닙니다: {p}")
    with zipfile.ZipFile(p) as zf:
        manifest = zf.read("META-INF/manifest.xml").decode("utf-8", "replace") if "META-INF/manifest.xml" in zf.namelist() else ""
        if "encryption-data" in manifest or any(i.flag_bits & 0x1 for i in zf.infolist()):
            raise ValueError(f"배포용(암호화) HWPX라 편집할 수 없습니다: {p.name}. "
                             "한컴오피스에서 배포용 설정을 해제한 사본(편집 권한 필요)으로 진행하세요.")


def _content_xml_names(zf: zipfile.ZipFile) -> list[str]:
    return [n for n in zf.namelist() if n.lower().endswith(".xml") and n.startswith("Contents/")] or \
           [n for n in zf.namelist() if n.lower().endswith(".xml")]


def _replace_in_text_nodes(xml: str, pairs: list[tuple[str, str]], counts: dict[int, int]) -> str:
    """텍스트 노드 본문 안에서만 치환한다. counts[i] += 치환 횟수."""
    esc = [(_escape(o), _escape(n)) for o, n in pairs]

    def fix(m: re.Match) -> str:
        body = m.group("body")
        for i, (o, n) in enumerate(esc):
            c = body.count(o)
            if c:
                body = body.replace(o, n)
                counts[i] = counts.get(i, 0) + c
        return m.group(1) + body + m.group(4)

    return TEXT_NODE.sub(fix, xml)


PREVIEW_TEXT = "Preview/PrvText.txt"


def _rewrite(src: str | Path, dst: str | Path, transform, preview_transform=None) -> dict:
    """transform(name, xml_str) -> xml_str 를 XML 엔트리에 적용해 새 파일을 쓴다.

    preview_transform(text) -> text 가 있으면 탐색기 미리보기 텍스트(Preview/PrvText.txt, UTF-8 평문)에도 적용한다.
    적용하지 않으면 파일 탐색기 미리보기에 옛 내용이 보인다.
    바뀌지 않은 엔트리는 원래 바이트·압축 방식 그대로 쓴다.
    """
    _check_hwpx(src)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    if Path(dst).resolve() == Path(src).resolve():
        raise ValueError("결과 파일이 원본과 같은 경로입니다. 원본은 덮어쓰지 않습니다.")
    changed: list[str] = []
    with zipfile.ZipFile(src) as zin:
        infos = zin.infolist()
        ordered = sorted(infos, key=lambda i: 0 if i.filename == "mimetype" else 1)  # mimetype 맨 앞
        with zipfile.ZipFile(dst, "w") as zout:
            for info in ordered:
                data = zin.read(info.filename)
                if info.filename.lower().endswith(".xml"):
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        text = None
                    if text is not None:
                        new = transform(info.filename, text)
                        if new != text:
                            new = LINESEG_PATTERN.sub("", new)
                            data = new.encode("utf-8")
                            changed.append(info.filename)
                elif info.filename == PREVIEW_TEXT and preview_transform is not None:
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        text = None
                    if text is not None:
                        new = preview_transform(text)
                        if new != text:
                            data = new.encode("utf-8")
                            changed.append(info.filename)
                ctype = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
                zout.writestr(info, data, compress_type=ctype)
    return {"output": str(dst), "changed_entries": changed}


def plan(hwpx_path: str, replacements: list[tuple[str, str]]) -> dict:
    """치환 대상별 출현 횟수와 위치를 미리 계산한다. 파일은 만들지 않는다."""
    _check_hwpx(hwpx_path)
    items = [{"old": o, "new": n, "count": 0, "entries": []} for o, n in replacements]
    with zipfile.ZipFile(hwpx_path) as zf:
        for name in _content_xml_names(zf):
            xml = zf.read(name).decode("utf-8", errors="replace")
            bodies = [m.group("body") for m in TEXT_NODE.finditer(xml)]
            for it in items:
                c = sum(b.count(_escape(it["old"])) for b in bodies)
                if c:
                    it["count"] += c
                    it["entries"].append(name)
    missing = [it["old"] for it in items if it["count"] == 0]
    hints = {}
    if missing:
        paras = extract_paragraphs(hwpx_path)
        for m in missing:
            near = [p for p in paras if m.replace(" ", "") in p.replace(" ", "")]
            hints[m] = (near[:2] and ["문단 전체에는 있지만 여러 텍스트 조각(run)으로 나뉘어 있습니다. extract 결과의 조각 단위로 나눠 지정하세요: "
                                     + " / ".join(near[:2])]) or ["문서에 없습니다. 띄어쓰기·특수문자를 extract 결과와 정확히 맞추세요."]
    return {"input": str(hwpx_path), "items": items, "missing": missing, "hints": hints}


def replace_texts(hwpx_path: str, replacements: list[tuple[str, str]], output_path: str,
                  strict: bool = True) -> str:
    """HWPX의 텍스트를 직접 치환해 새 파일로 저장한다(책 2장 API).

    strict=True면 찾지 못한 치환 대상이 하나라도 있을 때 아무 파일도 만들지 않고 ValueError를 낸다.
    """
    p = plan(hwpx_path, replacements)
    if p["missing"] and strict:
        detail = "\n".join(f"  - {m!r}: {p['hints'].get(m, [''])[0]}" for m in p["missing"])
        raise ValueError(f"찾지 못한 치환 대상 {len(p['missing'])}개(파일을 만들지 않았습니다):\n{detail}")
    counts: dict[int, int] = {}
    def preview(t: str) -> str:
        for o, n in replacements:
            t = t.replace(o, n)
        return t

    res = _rewrite(hwpx_path, output_path, lambda _n, x: _replace_in_text_nodes(x, replacements, counts), preview)
    total = sum(counts.values())
    print(f"  HWPX 생성 완료: {output_path} (치환 {total}건, 바뀐 항목 {len(res["changed_entries"])}개)")
    return output_path


def fill_template(template_path: str, data: dict, output_path: str,
                  placeholder_pattern: str = DEFAULT_PATTERN) -> str:
    """{{변수명}} 자리표시자를 data 값으로 채운다. 값은 XML 이스케이프한다."""
    pat = re.compile(placeholder_pattern)
    filled: set[str] = set()

    def transform(_name: str, xml: str) -> str:
        def fix(m: re.Match) -> str:
            def rep(mm: re.Match) -> str:
                key = mm.group(1)
                if key in data:
                    filled.add(key)
                    return _escape(str(data[key]))
                return mm.group(0)
            return m.group(1) + pat.sub(rep, m.group("body")) + m.group(4)
        return TEXT_NODE.sub(fix, xml)

    def preview(t: str) -> str:
        return pat.sub(lambda mm: str(data[mm.group(1)]) if mm.group(1) in data else mm.group(0), t)

    _rewrite(template_path, output_path, transform, preview)
    unfilled = [k for k in scan_placeholders(output_path, placeholder_pattern)]
    if unfilled:
        print(f"  경고: 채우지 못한 자리표시자 {unfilled}")
    print(f"  HWPX 생성 완료: {output_path} (자리표시자 {len(filled)}종 채움)")
    return output_path


def extract_texts(hwpx_path: str) -> list[str]:
    """모든 텍스트 조각(<hp:t>)을 순서대로 돌려준다. 치환 대상을 정확히 맞출 때 쓴다."""
    _check_hwpx(hwpx_path)
    out = []
    with zipfile.ZipFile(hwpx_path) as zf:
        for name in _content_xml_names(zf):
            xml = zf.read(name).decode("utf-8", errors="replace")
            for m in TEXT_NODE.finditer(xml):
                t = _visible(m.group("body")).strip()
                if t:
                    out.append(t)
    return out


def extract_paragraphs(hwpx_path: str) -> list[str]:
    """문단 단위로 조각을 이어 붙인 텍스트. 조각이 나뉜 위치를 찾을 때 쓴다."""
    _check_hwpx(hwpx_path)
    out = []
    with zipfile.ZipFile(hwpx_path) as zf:
        for name in _content_xml_names(zf):
            xml = zf.read(name).decode("utf-8", errors="replace")
            for pm in PARAGRAPH.finditer(xml):
                # 표 안 문단은 바깥 문단에 중첩되므로 가장 안쪽 문단만 의미가 있다. 조각만 이어 붙인다.
                t = "".join(_visible(m.group("body")) for m in TEXT_NODE.finditer(pm.group(0))).strip()
                if t:
                    out.append(t)
    return out


def scan_placeholders(template_path: str, placeholder_pattern: str = DEFAULT_PATTERN) -> list[str]:
    _check_hwpx(template_path)
    seen: list[str] = []
    with zipfile.ZipFile(template_path) as zf:
        for name in _content_xml_names(zf):
            xml = zf.read(name).decode("utf-8", errors="replace")
            for m in TEXT_NODE.finditer(xml):
                for k in re.findall(placeholder_pattern, _visible(m.group("body"))):
                    if k not in seen:
                        seen.append(k)
    return seen


def _load_map(path: str) -> list[tuple[str, str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.items())
    return [(d["old"], d["new"]) for d in data]


def main(argv: list[str]) -> int:
    import argparse
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="HWPX 양식 보존 텍스트 치환")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("input"); e.add_argument("--paragraphs", action="store_true")
    p = sub.add_parser("plan"); p.add_argument("input"); p.add_argument("--map", required=True)
    r = sub.add_parser("replace"); r.add_argument("input"); r.add_argument("--map", required=True)
    r.add_argument("--output", required=True); r.add_argument("--allow-missing", action="store_true")
    s = sub.add_parser("scan"); s.add_argument("input")
    f = sub.add_parser("fill"); f.add_argument("input"); f.add_argument("--data", required=True); f.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    try:
        return _dispatch(a)
    except (ValueError, FileNotFoundError) as err:
        print(f"오류: {err}")
        return 1


def _dispatch(a) -> int:
    if a.cmd == "extract":
        items = extract_paragraphs(a.input) if a.paragraphs else extract_texts(a.input)
        for i, t in enumerate(items, 1):
            print(f"{i:4}: {t}")
        return 0
    if a.cmd == "plan":
        res = plan(a.input, _load_map(a.map))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print("PLAN OK" if not res["missing"] else f"PLAN MISSING {len(res['missing'])}")
        return 0 if not res["missing"] else 1
    if a.cmd == "replace":
        try:
            replace_texts(a.input, _load_map(a.map), a.output, strict=not a.allow_missing)
        except ValueError as err:
            print(f"오류: {err}")
            return 1
        return 0
    if a.cmd == "scan":
        print(json.dumps(scan_placeholders(a.input), ensure_ascii=False))
        return 0
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    fill_template(a.input, data, a.output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
