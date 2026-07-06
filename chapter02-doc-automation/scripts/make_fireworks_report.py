#!/usr/bin/env python3
"""불꽃축제 결과보고서 생성 — HWPX 원본 양식의 텍스트만 교체."""

import re
import zipfile

SRC = "/Users/gangdasol/Downloads/결재문서본문_보고서 작성 서식 안내.hwpx"
DST = "/Users/gangdasol/Documents/git/claude-skills/chapter2-doc-automation/output/서울불꽃축제_결과보고.hwpx"

# (원본, 교체) 쌍
REPLACEMENTS = [
    # 제목
    ("보고서 작성 서식 안내", "2026 서울세계불꽃축제 결과보고"),
    # 부서명
    ("서울대공원", "서울시 문화본부"),
    # 수신자
    ("수신자참조", "문화체육관광부장관"),
    ("전략기획실장,운영과장,시설과장,조경과장", "문화정책과장,관광진흥과장,안전관리과장"),
    # 본문 1항
    (
        "1. 우리 관리부 보고서 작성시 부서별 기준이 없어 각종 보고서 작성시  통일하기 기하기 위하여 붙임과 같이 보고서 서식을 안내하오니,",
        "1. 2026 서울세계불꽃축제가 2026. 10. 3.(토) 19:30~21:00 여의도 한강공원 일대에서 성황리에 개최되었기에 그 결과를 아래와 같이 보고합니다.",
    ),
    # 본문 2항
    (
        "2. 전부서에서는 붙임 ",
        "2. 관람인원: 약 120만명(전년 대비 15% 증가), 안전사고 0건으로 ",
    ),
    (
        "\u201c보고서 서식\u201d",
        "\u201c안전하고 성공적인 축제\u201d",
    ),
    (
        "을 참조하여 통일되고 세련된 보고 문서를 작성하여 주시기 바랍니다. ",
        "로 평가되며, 시민 만족도 92.3%를 달성하였습니다.",
    ),
    # 붙임
    ("붙임 1. 겉표지 있는 보고서(계획서) 서식 1부", "붙임 1. 불꽃축제 결과 상세보고서 1부"),
    ("3. 붙임 서식 1부.  끝.", "3. 안전관리 결과보고서 1부.  끝."),
    # 결재선
    ("총무과장", "Sol 담당관"),
    ("총무과", "문화본부"),
    ("강준민", "Sol"),
    ("이행용", "Sol"),
    ("주무관", "담당관"),
    ("04/05", "10/05"),
    # 시행번호
    ("문화본부-4061", "문화본부-2026"),
    # 주소
    ("경기도 과천시 대공원광장로 102 서울대공원 문화본부", "서울시 중구 세종대로 110 서울시청 문화본부"),
    ("http://grandpark.seoul.go.kr/", "https://culture.seoul.go.kr/"),
    ("02-500-7210", "02-2133-2800"),
    ("02-500-7991", "02-2133-2899"),
    ("junmin@seoul.go.kr", "sol@seoul.go.kr"),
]


def main():
    with zipfile.ZipFile(SRC, "r") as zf_in:
        with zipfile.ZipFile(DST, "w") as zf_out:
            for name in zf_in.namelist():
                data = zf_in.read(name)
                info = zf_in.getinfo(name)
                compress = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED

                if name.endswith(".xml"):
                    xml_str = data.decode("utf-8")
                    for old, new in REPLACEMENTS:
                        xml_str = xml_str.replace(old, new)
                    # linesegarray 제거 (레이아웃 캐시 — 한컴에서 자동 재생성)
                    xml_str = re.sub(
                        r"<hp:linesegarray>.*?</hp:linesegarray>", "", xml_str, flags=re.DOTALL
                    )
                    data = xml_str.encode("utf-8")

                zf_out.writestr(info, data, compress_type=compress)

    print(f"생성 완료: {DST}")

    # 검증 출력
    with zipfile.ZipFile(DST, "r") as zf:
        xml = zf.read("Contents/section0.xml").decode("utf-8")
        texts = re.findall(r"<hp:t>(.*?)</hp:t>", xml)
        print("\n=== 변환 결과 주요 텍스트 ===")
        for i, t in enumerate(texts):
            t_clean = t.strip()
            if t_clean and len(t_clean) > 1:
                print(f"  {i:3d}: {t_clean}")


if __name__ == "__main__":
    main()
