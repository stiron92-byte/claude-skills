"""엑셀 정리 규칙 모음 — 전화번호·날짜·이메일·이상값·범주 표기 판정.

모든 함수는 '바꿔도 안전한가'를 함께 돌려준다. 안전하지 않으면 원래 값을 그대로 두고 사유를 붙인다.
사람이 판단해야 하는 값을 추측해서 고치면 원본보다 더 나쁜 데이터가 되기 때문이다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

# ───────────────────────── 전화번호 ─────────────────────────
AREA2 = {"02"}
AREA3 = {"031", "032", "033", "041", "042", "043", "044", "051", "052", "053", "054", "055", "061", "062", "063", "064", "070"}


def normalize_phone(value) -> tuple[str | None, str]:
    """(정규화 값 또는 None, 사유). None이면 바꾸지 않는다.

    지원: 휴대전화 010/011/016~019(10~11자리), +82·82 국가번호, 서울 02, 지역번호 3자리, 070, 대표번호 15xx/16xx/18xx.
    영문자 혼입(O↔0 등), 자릿수 오류는 고치지 않고 후보로 보고한다.
    """
    if value is None or (isinstance(value, float) and value != value):
        return None, "빈 값"
    s = str(value).strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        s = str(int(value))
        if len(s) == 10 and s.startswith("10"):  # 엑셀이 앞자리 0을 지운 휴대전화 번호
            s = "0" + s
    if re.search(r"[A-Za-z가-힣]", s):
        return None, "문자 혼입(예: 영문 O와 숫자 0 혼동) — 원본 확인 필요"
    digits = re.sub(r"\D", "", s)
    if digits.startswith("82") and len(digits) in (11, 12):
        digits = "0" + digits[2:]
    if len(digits) == 8 and digits[:2] in ("15", "16", "18"):
        return f"{digits[:4]}-{digits[4:]}", "대표번호"
    if digits.startswith("01") and len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}", "휴대전화"
    if digits.startswith("01") and len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", "휴대전화(구형 10자리)"
    if digits[:2] in AREA2 and len(digits) in (9, 10):
        mid = 3 if len(digits) == 9 else 4
        return f"02-{digits[2:2 + mid]}-{digits[2 + mid:]}", "서울"
    if digits[:3] in AREA3 and len(digits) in (10, 11):
        mid = 3 if len(digits) == 10 else 4
        return f"{digits[:3]}-{digits[3:3 + mid]}-{digits[3 + mid:]}", "지역번호"
    return None, f"자릿수·형식 오류({len(digits)}자리) — 원본 확인 필요"


# ───────────────────────── 날짜 ─────────────────────────
DATE_PATTERNS = [
    (re.compile(r"^(\d{4})[-./ ](\d{1,2})[-./ ](\d{1,2})\.?$"), "ymd"),
    (re.compile(r"^(\d{4})(\d{2})(\d{2})$"), "ymd"),
    (re.compile(r"^(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일$"), "ymd"),
    (re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$"), "xxY"),  # 월/일 또는 일/월
    (re.compile(r"^(\d{2})[-./](\d{1,2})[-./](\d{1,2})$"), "yyMD"),  # 두 자리 연도
]


def normalize_date(value, prefer: str | None = None) -> tuple[str | None, str]:
    """(YYYY-MM-DD 또는 None, 사유).

    - 날짜·시각 객체, 엑셀 일련번호(20000~80000)는 변환
    - 03/04/2024처럼 월·일이 모두 12 이하면 모호 → prefer("mdy"/"dmy")가 없으면 바꾸지 않는다
    - 두 자리 연도(24-03-04)는 세기 추측이 필요해 바꾸지 않는다
    """
    if value is None or (isinstance(value, float) and value != value):
        return None, "빈 값"
    if isinstance(value, datetime):
        return value.date().isoformat(), "날짜 형식"
    if isinstance(value, date):
        return value.isoformat(), "날짜 형식"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 20000 <= float(value) <= 80000:
            return (date(1899, 12, 30) + timedelta(days=int(value))).isoformat(), "엑셀 일련번호"
        return None, "숫자 — 날짜로 볼 수 없음"
    s = str(value).strip()
    for pat, kind in DATE_PATTERNS:
        m = pat.match(s)
        if not m:
            continue
        a, b, c = (int(x) for x in m.groups())
        try:
            if kind == "ymd":
                return date(a, b, c).isoformat(), "형식 통일"
            if kind == "yyMD":
                return None, "두 자리 연도 — 세기 확인 필요"
            if a > 12 >= b:
                return date(c, b, a).isoformat(), "일/월/연 형식"
            if b > 12 >= a:
                return date(c, a, b).isoformat(), "월/일/연 형식"
            if prefer == "mdy":
                return date(c, a, b).isoformat(), "월/일/연(지정)"
            if prefer == "dmy":
                return date(c, b, a).isoformat(), "일/월/연(지정)"
            return None, "월·일 순서가 모호(둘 다 12 이하) — 원본 확인 필요"
        except ValueError:
            return None, "존재하지 않는 날짜"
    return None, "날짜 형식을 해석할 수 없음"


# ───────────────────────── 이메일 ─────────────────────────
COMMON_DOMAINS = ["gmail.com", "naver.com", "daum.net", "hanmail.net", "kakao.com", "nate.com", "yahoo.com",
                  "hotmail.com", "outlook.com", "icloud.com"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def email_issue(value) -> tuple[str | None, str | None]:
    """(문제 유형, 제안 도메인). 문제 없으면 (None, None). 이메일은 고치지 않고 후보로만 보고한다."""
    if value is None or str(value).strip() == "":
        return None, None
    s = str(value).strip()
    if not EMAIL_RE.match(s):
        return "형식 오류", None
    domain = s.split("@")[1].lower()
    if domain in COMMON_DOMAINS:
        return None, None
    best = min(COMMON_DOMAINS, key=lambda d: levenshtein(domain, d))
    if levenshtein(domain, best) <= 2:
        return "도메인 오타 의심", best
    return None, None


# ───────────────────────── 이상값 ─────────────────────────
def outliers(values: list[float], k: float = 3.0) -> list[int]:
    """사분위 범위(IQR) 기준 극단값 위치. k=3이면 '매우 극단'만 잡는다(일반 변동은 남긴다)."""
    xs = sorted(v for v in values if v is not None)
    if len(xs) < 8:
        return []
    def q(p):
        i = (len(xs) - 1) * p
        lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
        return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)
    q1, q3 = q(0.25), q(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return []
    lo, hi = q1 - k * iqr, q3 + k * iqr
    return [i for i, v in enumerate(values) if v is not None and (v < lo or v > hi)]


# ───────────────────────── 범주 표기 ─────────────────────────
def category_key(s: str) -> str:
    t = re.sub(r"\s+", "", str(s))
    for a, b in (("특별시", ""), ("광역시", ""), ("특별자치시", ""), ("특별자치도", ""), ("시", ""), ("도", "")):
        t = t.replace(a, b)
    return t.lower()


def category_variants(values: list) -> list[list[str]]:
    """같은 값을 다르게 쓴 묶음. 예: ['서울 강남구', '서울시 강남구']"""
    groups: dict[str, set] = {}
    for v in values:
        if v is None or str(v).strip() == "":
            continue
        groups.setdefault(category_key(v), set()).add(str(v))
    return [sorted(g) for g in groups.values() if len(g) > 1]
