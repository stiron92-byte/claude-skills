"""meeting-minutes 테스트 공통 경로·기준 회의록."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/kevin-skills-book/skills/meeting-minutes"
SCRIPTS = SKILL / "scripts"
SAMPLES = ROOT / "plugins/kevin-skills-practice/skills/practice-samples/samples/meeting-minutes"
INPUTS = SAMPLES / "inputs"
AUDIO = SAMPLES / "example"
TEXT = INPUTS / "마케팅주간회의_녹취록.txt"
KEY = json.loads((INPUTS / "answer_key.json").read_text(encoding="utf-8"))
VENV_PY = ROOT / ".workspace/pins-venv/Scripts/python.exe"

# 텍스트 녹취록(마케팅 주간회의)의 기준 회의록. 발언 번호는 prepare_transcript.py 결과 기준
GOOD_MINUTES = {
    "meta": {"title": "마케팅 주간회의(3월 둘째 주)", "date": "2026-03-09", "time": "오전 10:00",
             "attendees": ["김민지", "이준호", "박서연", "최동훈"], "absent": ["정하늘(휴가)"],
             "role": "PM", "purpose": "report", "language": "ko", "corrections": []},
    "summary": ["봄 프로모션 오픈을 물류 입고 지연(3월 27일)으로 3월 30일 월요일로 한 주 미뤘다.",
                "광고 예산 4,500만 원을 검색 2,000만 원, SNS 1,500만 원, 예비 1,000만 원으로 확정했다."],
    "agenda": [
        {"title": "봄 프로모션 오픈 일정", "points": ["3월 23일 오픈 예정이었으나 상품 입고가 3월 27일로 밀림", "오픈을 3월 30일로 변경, 23일 안 취소"],
         "evidence": ["T0003", "T0006", "T0008"]},
        {"title": "광고 예산 배분", "points": ["총 4,500만 원", "지난 겨울 전환율 2.8%, 이번 목표 3.5%", "SNS 비중 확대는 첫 주 성과 후 재논의"],
         "evidence": ["T0011", "T0012", "T0013", "T0015"]},
        {"title": "고객 문의 대응", "points": ["지난 프로모션 첫 주 하루 평균 120건, 응답 평균 4시간", "배송 일정·쿠폰 사용법·교환 반품이 문의의 70%"],
         "evidence": ["T0024", "T0025"]},
    ],
    "decisions": [
        {"text": "봄 프로모션 오픈일을 3월 30일 월요일로 변경한다(3월 23일 안 취소)", "evidence": ["T0008"]},
        {"text": "광고 예산은 검색광고 2,000만 원, SNS 광고 1,500만 원, 예비비 1,000만 원으로 확정한다", "evidence": ["T0012", "T0015"]},
        {"text": "자주 묻는 질문 세 가지(배송 일정·쿠폰 사용법·교환 반품)는 챗봇으로 먼저 처리한다", "evidence": ["T0025", "T0026"]},
    ],
    "action_items": [
        {"task": "물류팀에 재고 수량을 다시 확인해 공유", "owner": "이준호", "due": "수요일(3/11)", "evidence": ["T0009"]},
        {"task": "광고 소재 3종 제작·업로드", "owner": "최동훈", "due": "이번 주 금요일(3/13)", "evidence": ["T0016"]},
        {"task": "랜딩 페이지 문구 검수", "owner": "미정(정하늘 복귀 후 결정)", "due": "오픈 전", "evidence": ["T0017", "T0020"]},
        {"task": "챗봇 시나리오 초안 작성", "owner": "박서연", "due": "미정", "evidence": ["T0027"]},
        {"task": "인플루언서 협업 후보 추리기", "owner": "최동훈", "due": "다음 회의 전", "evidence": ["T0029"]},
    ],
    "open_questions": [
        {"text": "인플루언서 협업 여부 — 예산 문제로 다음 회의 안건", "evidence": ["T0029"]},
        {"text": "SNS 광고 비중 확대 — 첫 주 성과를 보고 재논의", "evidence": ["T0014", "T0015"]},
    ],
    "next_meeting": {"text": "3월 16일 월요일 오전 10시", "evidence": ["T0032"]},
    "sections": [{"title": "리스크 및 이슈", "items": [{"text": "상품 입고가 3월 27일보다 더 늦어지면 오픈일 재조정 필요", "evidence": ["T0006"]}]}],
    "uncertain": [],
}


def run_script(name: str, *args, python: str | None = None, timeout: int = 900) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([python or sys.executable, str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=timeout)
