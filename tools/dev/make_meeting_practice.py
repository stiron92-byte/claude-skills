#!/usr/bin/env python3
"""meeting-minutes 실습 텍스트 녹취록과 정답표(녹음 3개 + 텍스트 1개)를 만든다. 매번 같은 결과가 나온다.

왜
- v1.6.1 실습은 녹음 3개뿐이고 정답이 없어 "회의록이 맞게 정리됐는지" 확인할 방법이 없었다.
- 실제 업무에서는 클로바노트·노션·Zoom이 만든 텍스트를 붙여 넣는 경우가 많다. 그 입력을 연습할 파일이 필요하다.

텍스트 녹취록에 일부러 넣은 함정
- 결정 번복: 출시일 3월 23일 합의 → 물류 문제로 3월 30일로 변경(최종만 결정 사항)
- 담당자 없는 할 일(랜딩 문구 검수), 기한 없는 할 일(챗봇 시나리오 초안)
- 결정이 아닌 의견(SNS 비중 확대 검토), 다음 회의로 미룬 안건(인플루언서 협업)
- 불참자 언급(정하늘 휴가), 회의와 무관한 잡담(점심)

녹음 정답표는 원래 대본을 구할 수 없어, base·small 두 모델의 변환 결과와 맥락을 대조해 정했다.
STT가 틀리게 적는 부분(stt_traps)과, 녹음만으로 확정할 수 없는 부분(unclear)을 따로 적었다.

사용법: python tools/dev/make_meeting_practice.py [--check]
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/meeting-minutes/inputs"
TEXT_NAME = "마케팅주간회의_녹취록.txt"

# (화자, 시각, 발언)
LINES = [
    ("김민지", "00:00", "네, 시작할게요. 3월 둘째 주 마케팅 주간회의입니다. 하늘 님은 오늘 휴가라서 빠지셨고요, 준호 님, 서연 님, 동훈 님 이렇게 넷이 진행하겠습니다."),
    ("김민지", "00:14", "안건은 세 개예요. 봄 프로모션 오픈 일정, 광고 예산 배분, 그리고 고객 문의 대응 건입니다."),
    ("김민지", "00:25", "첫 번째, 봄 프로모션 오픈 일정부터요. 지난주에 3월 23일 오픈으로 잡았었죠?"),
    ("이준호", "00:32", "네, 23일 월요일로 잡았습니다. 상세 페이지랑 쿠폰 설정은 다 끝났어요."),
    ("김민지", "00:40", "좋아요. 그럼 23일 오픈으로 그대로 가죠."),
    ("박서연", "00:44", "잠깐만요, 오늘 아침에 물류팀에서 연락이 왔는데 프로모션 상품 입고가 3월 27일로 밀렸대요."),
    ("이준호", "00:53", "아, 그러면 23일에 열면 나흘 동안 품절 상태로 보이겠네요."),
    ("김민지", "00:59", "그건 안 되죠. 그럼 오픈을 한 주 미뤄서 3월 30일 월요일로 하겠습니다. 23일 안은 취소할게요."),
    ("이준호", "01:08", "네, 30일로 다시 설정하겠습니다. 물류팀에 재고 수량 다시 확인해서 수요일까지 공유드릴게요."),
    ("김민지", "01:17", "네, 부탁해요."),
    ("김민지", "01:20", "두 번째, 광고 예산입니다. 이번 프로모션 광고 예산은 총 4,500만 원이에요."),
    ("최동훈", "01:29", "제안드리면 검색광고 2,000만 원, SNS 광고 1,500만 원, 나머지 1,000만 원은 예비비로 두는 게 어떨까 합니다."),
    ("최동훈", "01:40", "지난 겨울 프로모션 때 전환율이 2.8%였는데, 이번에는 3.5%를 목표로 잡고 있어요."),
    ("박서연", "01:49", "요즘 SNS 반응이 좋아서 SNS 비중을 좀 더 늘리는 것도 생각해 볼 만한 것 같아요."),
    ("김민지", "01:56", "그건 첫 주 성과를 보고 다시 얘기하죠. 일단 동훈 님 안대로 2,000, 1,500, 1,000으로 확정합니다."),
    ("최동훈", "02:05", "네. 그럼 광고 소재 3종은 이번 주 금요일까지 만들어서 올리겠습니다."),
    ("김민지", "02:12", "아 그리고 랜딩 페이지 문구 검수도 해야 하는데, 이건 누가 하죠?"),
    ("이준호", "02:18", "저는 이번 주에 재고 건이 있어서 좀 어렵고요."),
    ("박서연", "02:22", "저도 챗봇 건 때문에 확답은 어려울 것 같아요."),
    ("김민지", "02:27", "음, 그럼 담당자는 하늘 님 복귀하면 다시 정하죠. 검수 자체는 오픈 전에 꼭 끝나야 해요."),
    ("이준호", "02:35", "근데 오늘 점심 뭐 먹어요? 회사 앞에 국숫집 새로 생겼던데요."),
    ("최동훈", "02:40", "오 거기 괜찮다던데요, 이따 가보죠."),
    ("김민지", "02:44", "하하, 회의 끝나고 정해요. 세 번째 안건, 고객 문의 대응입니다."),
    ("박서연", "02:51", "지난 프로모션 때 첫 주 문의가 하루 평균 120건이었어요. 상담원 두 명으로는 응답이 평균 4시간씩 걸렸습니다."),
    ("박서연", "03:02", "자주 묻는 질문은 챗봇으로 먼저 받으면 좋겠어요. 배송 일정, 쿠폰 사용법, 교환 반품 이렇게 세 가지가 문의의 70%였거든요."),
    ("김민지", "03:13", "좋네요. 챗봇으로 자주 묻는 질문 세 가지를 먼저 처리하는 걸로 하죠."),
    ("박서연", "03:19", "네, 그럼 챗봇 시나리오 초안은 제가 만들어 볼게요."),
    ("최동훈", "03:24", "그리고 인플루언서 협업도 이번에 해 볼지 얘기가 있었는데요."),
    ("김민지", "03:30", "그건 예산이 걸려 있으니까 다음 회의 안건으로 넘기죠. 동훈 님이 후보만 몇 명 추려 와 주세요."),
    ("최동훈", "03:38", "네, 알겠습니다."),
    ("김민지", "03:41", "정리할게요. 오픈은 3월 30일, 광고 예산은 검색 2,000만 원, SNS 1,500만 원, 예비 1,000만 원, 그리고 챗봇으로 자주 묻는 질문 세 가지를 먼저 받습니다."),
    ("김민지", "03:55", "다음 회의는 3월 16일 월요일 오전 10시에 하겠습니다. 수고하셨어요."),
    ("이준호", "04:01", "수고하셨습니다."),
]
HEADER = ["마케팅 주간회의", "2026.03.09 월 오전 10:00 ・ 4분 5초", "김민지  이준호  박서연  최동훈", ""]

TEXT_KEY = {
    "source": TEXT_NAME,
    "format": "클로바노트 내보내기 형식(머리글 + '화자 mm:ss' 줄 + 발언 줄)",
    "date": "2026-03-09",
    "attendees": ["김민지", "이준호", "박서연", "최동훈"],
    "absent": ["정하늘"],
    "decisions": [
        {"key": "오픈일", "must": ["3월 30일"], "note": "3월 23일 안은 취소(번복)"},
        {"key": "광고 예산", "must": ["2,000만", "1,500만", "1,000만"], "note": "총 4,500만 원"},
        {"key": "챗봇", "must": ["챗봇"], "note": "자주 묻는 질문 3가지(배송 일정·쿠폰·교환 반품) 우선 처리"},
    ],
    "superseded": ["3월 23일 오픈"],
    "not_decisions": ["SNS 비중 확대(첫 주 성과 후 재논의)", "인플루언서 협업(다음 회의 안건)"],
    "actions": [
        {"task": "물류팀 재고 수량 재확인 후 공유", "owner": "이준호", "due": "수요일"},
        {"task": "광고 소재 3종 제작·업로드", "owner": "최동훈", "due": "금요일"},
        {"task": "랜딩 페이지 문구 검수", "owner": "미정", "due": "오픈 전(3월 30일 전)", "note": "담당자는 정하늘 복귀 후 결정"},
        {"task": "챗봇 시나리오 초안", "owner": "박서연", "due": "미정"},
        {"task": "인플루언서 후보 추리기", "owner": "최동훈", "due": "다음 회의(3월 16일) 전", "note": "기한은 녹취에 명시되지 않은 추론. '미정'도 정답"},
    ],
    "open_questions": ["인플루언서 협업 여부 — 다음 회의", "SNS 비중 확대 — 첫 주 성과 후"],
    "numbers": ["4,500만", "2,000만", "1,500만", "1,000만", "2.8%", "3.5%", "120건", "4시간", "70%", "3월 27일"],
    "next_meeting": "2026-03-16(월) 오전 10시",
    "off_topic": ["점심 메뉴(국숫집)"],
}

AUDIO_KEYS = {
    "test_sprint_meeting_ko.mp3": {
        "language": "ko",
        "attendees": ["김PM", "이개발", "박디자인", "정기획"],
        "decisions": [
            {"key": "스프린트 목표", "must": ["로그인"]},
            {"key": "소셜 로그인 이월", "must": ["소셜", "다음 스프린트"]},
        ],
        "actions": [
            {"task": "백엔드 API 마무리", "owner": "이개발", "due": "금요일"},
            {"task": "메일 발송 서비스 옵션 검토 후 슬랙 공유", "owner": "이개발", "due": "내일"},
            {"task": "로그인 UI 퍼블리싱 전달", "owner": "박디자인", "due": "수요일"},
            {"task": "회원가입 페이지", "owner": "박디자인", "due": "목요일"},
            {"task": "기획서 업데이트(비밀번호 찾기 이메일 인증)", "owner": "정기획", "due": "내일"},
        ],
        "numbers": ["70%"],
        "next_meeting": "금요일 오후 2시(small 모델 인식. base 모델은 '52시'로 오인식)",
        "stt_traps": {"김 피암": "김PM", "정기회": "정기획", "유월": "이월", "매일 발송/매일 서비스": "메일 발송/메일 서비스",
                      "AWS ss": "AWS SES(추정)", "퍼글리싱": "퍼블리싱", "백앤드 에이페이": "백엔드 API", "52시": "오후 2시"},
        "unclear": [],
    },
    "test_planning_meeting_ko.mp3": {
        "language": "ko",
        "date": "2024-03-15",
        "attendees": ["최부장", "김과장", "이대리", "박사원"],
        "decisions": [
            {"key": "구독 가격", "must": ["11,900"], "note": "모델마다 다르게 인식된다. 제안 발언은 small 2회·medium·base+사전 4번 모두 '만천구백원'(11,900). 결정 발언은 small 11,900, medium·base+사전 1,900('만' 누락), base만 19,900 — 녹음 확인 권장"},
            {"key": "베타 론칭", "must": ["4월 28일"]},
            {"key": "AI 추천 단계 적용", "must": ["규칙", "정식"]},
        ],
        "actions": [
            {"task": "가격 정책 상세안 제출", "owner": "김과장", "due": "다음 주 월요일(medium 인식)"},
            {"task": "결제 시스템 개발 착수·기술 로드맵 공유", "owner": "이대리", "due": "수요일"},
            {"task": "인플루언서 리스트·상세 예산안", "owner": "박사원", "due": "금요일"},
            {"task": "이사회 중간 보고", "owner": "최부장", "due": "다음 주 수요일"},
        ],
        "numbers": ["3억", "1억 5천", "9,900", "14,900", "30%", "4주", "3개월", "50%", "5명", "2,000만", "1,000명(얼리버드, medium 인식)"],
        "next_meeting": "3월 22일 금요일 오전 10시",
        "stt_traps": {"월 1,900원": "'만' 누락 오인식(11,900) — 그대로 쓰면 오류", "월 19,900원(base 결정 발언)": "다른 모델은 11,900으로 인식 — 확인 필요", "이데리": "이대리",
                      "배타": "베타", "구동 모델": "구독 모델", "올리버드": "얼리버드", "인플로언서": "인플루언서", "이주면": "2주면(추정)"},
        "unclear": ["구독 가격(11,900 추정, 위 note)", "얼리버드 목표 인원(base·small '3명' — medium '1,000명')", "김과장 제출 기한(base '어려울까지' — medium '다음 주 월요일')"],
    },
    "test_project_meeting_en.mp3": {
        "language": "en",
        "attendees": ["Sarah", "Mike", "Jenny"],
        "decisions": [
            {"key": "dark mode deferred", "must": ["dark mode"], "note": "다음 주로 미루고 먼저 추정"},
            {"key": "bug fix backend only", "must": ["backend"], "note": "UI·스크린샷 변경 없음"},
        ],
        "actions": [
            {"task": "payment bug fix", "owner": "Mike", "due": "tomorrow (afternoon)"},
            {"task": "load testing", "owner": "Mike", "due": "Friday"},
            {"task": "upload onboarding screens to Figma", "owner": "Jenny", "due": "today"},
            {"task": "dark mode estimate & impact analysis", "owner": "Jenny", "due": "Monday"},
            {"task": "final product screenshots to Sarah", "owner": "미정(Sarah가 요청)", "due": "Thursday"},
            {"task": "email campaign start", "owner": "Sarah", "due": "next Monday"},
        ],
        "numbers": ["12%", "10,000", "30", "two engineers"],
        "next_meeting": "Friday 10am",
        "stt_traps": {"It fixes(T0029)": "Mike fixes", "a be testing": "A/B testing"},
        "unclear": [],
    },
}


def write(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    body = HEADER + [x for sp, t, text in LINES for x in (f"{sp} {t}", text, "")]
    (target / TEXT_NAME).write_text("\n".join(body), encoding="utf-8")
    key = {"generated_by": "tools/dev/make_meeting_practice.py", "text": TEXT_KEY, "audio": AUDIO_KEYS}
    (target / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as td:
            write(Path(td))
            diff = [n for n in (TEXT_NAME, "answer_key.json")
                    if (Path(td) / n).read_bytes() != (OUT / n).read_bytes()]
        print("DIFF: " + ", ".join(diff) if diff else "REPRODUCIBLE")
        return 1 if diff else 0
    write(OUT)
    print(f"written: {OUT / TEXT_NAME}, {OUT / 'answer_key.json'} ({len(LINES)}개 발언)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
