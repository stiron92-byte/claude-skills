#!/usr/bin/env python3
"""P4 오라클: hwpx-editor 치환 엔진과 검증기를 실제 실습 양식으로 확인한다.

1. 책 실습 2-7 형태의 직접 치환 → verify 통과, 비XML 엔트리 바이트 동일
2. 없는 텍스트가 섞인 치환 맵 → strict 모드에서 파일을 만들지 않고 실패
3. {{자리표시자}} 양식 채우기(실습 데이터) → 남은 자리표시자 0, verify 통과
4. 특수문자(&, <, >)가 든 새 텍스트 → XML이 깨지지 않고 글자가 그대로 보인다
5. 양성 대조: mimetype 압축, 엔트리 삭제, 태그 속성 변경, 원문 잔존을 verify가 각각 잡는다
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "plugins/kevin-skills-book/skills/hwpx-editor/scripts"
S = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/doc-automation/example/example_4_hwpx-template"
sys.path.insert(0, str(H))
import hwpx_template as ht  # noqa: E402
import verify_hwpx as vh  # noqa: E402

ORIG = S / "원본_결재문서본문.hwpx"
TPL = S / "결재문서_템플릿.hwpx"
MAP = [("서울대공원", "한강사업본부"), ("보고서 작성 서식 안내", "2026 서울세계불꽃축제 운영 결과 보고"),
       ("강준민", "김한강"), ("이행용", "박여의")]


def rezip(src: Path, dst: Path, mutate) -> None:
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w") as zo:
        for info in zi.infolist():
            r = mutate(info, zi.read(info.filename))
            if r is None:
                continue
            data, ctype = r
            zo.writestr(info, data, compress_type=ctype)


def main() -> int:
    for s in (sys.stdout,):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # 1
        out = td / "result.hwpx"
        ht.replace_texts(str(ORIG), MAP, str(out))
        r = vh.verify(str(ORIG), str(out), MAP)
        if not r["ok"]:
            problems.append(f"1 직접 치환 verify 실패: {r['errors']}")
        with zipfile.ZipFile(ORIG) as a, zipfile.ZipFile(out) as b:
            for n in a.namelist():
                if n == "Preview/PrvText.txt":
                    if "한강사업본부" not in b.read(n).decode("utf-8"):
                        problems.append("1 탐색기 미리보기 텍스트가 갱신되지 않음")
                    continue
                if not n.endswith(".xml") and a.read(n) != b.read(n):
                    problems.append(f"1 비XML 엔트리 변경: {n}")
            if b.infolist()[0].filename != "mimetype":
                problems.append("1 mimetype이 첫 엔트리가 아님")
        # 2
        bad = td / "should_not_exist.hwpx"
        try:
            ht.replace_texts(str(ORIG), MAP + [("존재하지않는문구XYZ", "x")], str(bad))
            problems.append("2 누락 대상이 있는데 예외가 없음")
        except ValueError as e:
            if "존재하지않는문구XYZ" not in str(e):
                problems.append("2 오류 메시지에 누락 대상이 없음")
        if bad.exists():
            problems.append("2 strict 실패인데 파일이 생성됨")
        # 3
        import json
        data = json.loads((S / "fireworks_data.json").read_text(encoding="utf-8"))
        filled = td / "filled.hwpx"
        ht.fill_template(str(TPL), data, str(filled))
        if ht.scan_placeholders(str(filled)):
            problems.append(f"3 남은 자리표시자: {ht.scan_placeholders(str(filled))}")
        r = vh.verify(str(TPL), str(filled))
        if not r["ok"]:
            problems.append(f"3 양식 채우기 verify 실패: {r['errors']}")
        if "김한강" not in "\n".join(ht.extract_texts(str(filled))):
            problems.append("3 채운 값이 보이지 않음")
        # 4
        special = td / "special.hwpx"
        ht.replace_texts(str(ORIG), [("보고서 작성 서식 안내", "R&D 과제 <2026> 결과")], str(special))
        r = vh.verify(str(ORIG), str(special), [("보고서 작성 서식 안내", "R&D 과제 <2026> 결과")])
        if not r["ok"]:
            problems.append(f"4 특수문자 치환 verify 실패: {r['errors']}")
        if "R&D 과제 <2026> 결과" not in ht.extract_texts(str(special)):
            problems.append("4 특수문자 텍스트가 그대로 보이지 않음")
        # 5 양성 대조
        controls = {
            "mimetype 압축": lambda i, d: (d, zipfile.ZIP_DEFLATED),
            "엔트리 삭제": lambda i, d: None if i.filename.startswith("BinData/") or i.filename.endswith("settings.xml") else (d, i.compress_type if i.filename != "mimetype" else zipfile.ZIP_STORED),
            "속성 변경": lambda i, d: ((d.replace(b'id="', b'id="9', 1) if i.filename.startswith("Contents/section") else d),
                                    zipfile.ZIP_STORED if i.filename == "mimetype" else i.compress_type),
        }
        for label, mut in controls.items():
            t = td / f"ctl_{len(label)}.hwpx"
            rezip(out, t, mut)
            if vh.verify(str(ORIG), str(t), MAP)["ok"]:
                problems.append(f"5 양성 대조 '{label}'을 잡지 못함")
        # 원문 잔존: 치환하지 않은 파일을 결과로 주장
        if vh.verify(str(ORIG), str(ORIG), MAP)["ok"]:
            problems.append("5 양성 대조 '원문 잔존'을 잡지 못함")
    for p in problems:
        print("FAIL:", p)
    if problems:
        return 1
    print("replace/strict/fill/escape ok; controls detected: mimetype, removed entry, attribute change, original text")
    print("HWPX EDITOR OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
