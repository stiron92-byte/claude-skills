#!/usr/bin/env python3
"""한글 폰트 탐색 (Windows / macOS / Linux 공통).

스킬마다 폰트 경로를 하드코딩하면 OS가 바뀔 때 한글이 깨진다(□□□).
이 모듈이 한 곳에서 탐색하고, matplotlib·Pillow·ffmpeg가 쓸 경로를 돌려준다.

탐색 순서
1. 환경 변수 CLAUDE_SKILLS_FONT (사용자가 지정한 폰트 파일)
2. OS별 알려진 경로(아래 CANDIDATES)
3. fc-list 결과(Linux/macOS, fontconfig가 있을 때)

CLI:
    python fonts.py            # {"regular": "...", "bold": "...", "family": "..."} 출력
    python fonts.py --check    # 찾으면 exit 0, 못 찾으면 exit 1
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

_WIN_FONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

CANDIDATES: dict[str, dict[str, list[str]]] = {
    "Windows": {
        "regular": [str(_WIN_FONTS / "malgun.ttf"), str(_WIN_FONTS / "NanumGothic.ttf"), str(_WIN_FONTS / "gulim.ttc")],
        "bold": [str(_WIN_FONTS / "malgunbd.ttf"), str(_WIN_FONTS / "NanumGothicBold.ttf")],
    },
    "Darwin": {
        "regular": [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/NanumGothic.ttf",
        ],
        "bold": ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/NanumGothicBold.ttf"],
    },
    "Linux": {
        "regular": [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        ],
        "bold": [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        ],
    },
}

# matplotlib family 이름 (파일명 → family)
_FAMILY_BY_STEM = {
    "malgun": "Malgun Gothic",
    "malgunbd": "Malgun Gothic",
    "NanumGothic": "NanumGothic",
    "NanumGothicBold": "NanumGothic",
    "gulim": "Gulim",
    "AppleSDGothicNeo": "Apple SD Gothic Neo",
    "AppleGothic": "AppleGothic",
    "NotoSansCJK-Regular": "Noto Sans CJK KR",
    "NotoSansCJK-Bold": "Noto Sans CJK KR",
}

INSTALL_HINT = {
    "Windows": "Windows 기본 '맑은 고딕'이 없으면 설정 > 개인 설정 > 글꼴에서 한국어 글꼴을 추가하세요.",
    "Darwin": "macOS에는 Apple SD Gothic Neo가 기본 포함됩니다. 없으면 brew install --cask font-nanum-gothic",
    "Linux": "sudo apt-get install -y fonts-noto-cjk  (또는 fonts-nanum)",
}


def _fc_list() -> list[str]:
    if not shutil.which("fc-list"):
        return []
    try:
        out = subprocess.run(["fc-list", ":lang=ko", "file"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    return [line.split(":")[0].strip() for line in out.splitlines() if line.strip()]


def find_font(weight: str = "regular", system: str | None = None) -> str | None:
    """한글을 표시할 수 있는 폰트 파일 경로를 돌려준다. 없으면 None."""
    env = os.environ.get("CLAUDE_SKILLS_FONT")
    if env and Path(env).is_file():
        return env
    system = system or platform.system()
    for p in CANDIDATES.get(system, {}).get(weight, []) + CANDIDATES.get(system, {}).get("regular", []):
        if Path(p).is_file():
            return p
    found = _fc_list()
    if weight == "bold":
        bold = [f for f in found if "bold" in f.lower()]
        if bold:
            return bold[0]
    return found[0] if found else None


def family_for(path: str | None) -> str | None:
    if not path:
        return None
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]  # Linux에서도 Windows 경로를 읽는다
    return _FAMILY_BY_STEM.get(Path(name).stem)


def configure_matplotlib() -> str | None:
    """matplotlib 기본 폰트를 한글 폰트로 설정하고 사용한 family 이름을 돌려준다."""
    path = find_font()
    if not path:
        return None
    try:
        from matplotlib import font_manager, rcParams  # type: ignore
    except ImportError:
        return None
    font_manager.fontManager.addfont(path)
    family = font_manager.FontProperties(fname=path).get_name()
    rcParams["font.family"] = family
    rcParams["axes.unicode_minus"] = False  # 한글 폰트에서 마이너스 기호 깨짐 방지
    return family


def ffmpeg_fontfile(path: str | None) -> str | None:
    """ffmpeg drawtext/subtitles 필터에 넣을 수 있게 경로를 이스케이프한다.

    Windows의 'C:\\Windows\\Fonts\\malgun.ttf'는 필터 문법에서 ':'와 '\\'가 특수문자라
    'C\\:/Windows/Fonts/malgun.ttf' 형태로 바꿔야 한다.
    """
    if not path:
        return None
    p = path.replace("\\", "/")
    return p.replace(":", "\\:")


def describe() -> dict:
    system = platform.system()
    regular = find_font("regular")
    bold = find_font("bold")
    return {
        "os": system,
        "regular": regular,
        "bold": bold,
        "family": family_for(regular),
        "ffmpeg_fontfile": ffmpeg_fontfile(regular),
        "hint": None if regular else INSTALL_HINT.get(system, "한글 폰트를 설치하세요."),
    }


def main(argv: list[str]) -> int:
    info = describe()
    if "--check" in argv:
        print("FONT OK" if info["regular"] else f"FONT MISSING: {info['hint']}")
        return 0 if info["regular"] else 1
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
