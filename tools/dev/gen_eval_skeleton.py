#!/usr/bin/env python3
"""스킬별 smoke eval 케이스 골격을 생성한다(이미 있는 케이스는 건드리지 않는다).

형식: claude plugin eval 문서(code.claude.com/docs/en/plugin-evals)
  plugins/<plugin>/evals/<case>/prompt.md        (frontmatter + 사용자 요청)
  plugins/<plugin>/evals/<case>/graders/*.md     (frontmatter type + 필드, llm은 본문이 루브릭)

각 케이스는 '스킬이 발화했는가'(tool_used: Skill, 점수 제외 지표)와
'결과가 기대에 맞는가'(file_exists / llm 등, 점수 대상)를 한 쌍 이상 갖는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CSV = """날짜,상품명,매출,판매량
2026-09-21,무선 이어폰,1200000,40
2026-09-22,무선 이어폰,900000,30
2026-09-22,보조배터리,300000,15
2026-09-23,보조배터리,450000,22
2026-09-24,스마트워치,2100000,12"""

TRANSCRIPT = """김PM: 이번 주 스프린트 리뷰 시작할게요. 결제 모듈은 어떻게 됐나요?
이개발: 카드 결제는 끝났고 간편결제 연동이 남았습니다. 금요일까지 마무리하겠습니다.
박디자인: 결제 완료 화면 시안은 오늘 공유드릴게요.
김PM: 좋아요. 간편결제는 이개발님이 금요일까지, 시안은 박디자인님이 오늘 중으로. 다음 회의는 다음 주 월요일 10시로 하죠."""

BLOG = """1인 개발자가 첫 수익을 내기까지 걸린 시간은 8개월이었다. 처음 6개월은 기능만 만들었고 사용자는 늘지 않았다.
바뀐 계기는 사용자 인터뷰 10번이었다. 사람들은 기능이 아니라 '시간 절약'에 돈을 낸다는 걸 알게 됐다.
그 뒤로 랜딩 페이지 문구를 기능 나열에서 '하루 30분 절약'으로 바꿨고, 전환율이 2배가 됐다."""


def skill_grader(skill: str) -> str:
    return f"""---
type: tool_used
tool: Skill
input_match: '"skill"\\s*:\\s*"(?:[\\w-]+:)?{skill}"'
---
"""


CASES = {
    "kevin-skills-book": [
        ("doc-automation-csv-weekly-report", "doc-automation", ["smoke"], 20, ["Bash", "Write", "Edit", "Read"],
         f"아래 주간 매출 데이터로 팀장님께 보고할 주간 보고 PPT를 만들어서 report/weekly.pptx 로 저장해줘.\n\n```csv\n{CSV}\n```",
         {"pptx-exists.md": "---\ntype: file_exists\npath: report/weekly.pptx\n---\n"}),
        ("hwpx-editor-asks-for-form", "hwpx-editor", ["smoke"], 6, ["Bash", "Read"],
         "이 결재문서 양식을 그대로 사용해서 서울 불꽃축제 운영 결과 보고서로 바꿔줘. 기관명은 한강사업본부, 담당자는 김한강, 결재자는 박여의로 해줘.",
         {"asks-file.md": "---\ntype: llm\n---\n작업 폴더에 HWPX 파일이 없다. 응답이 원본 .hwpx 양식 파일을 요청하거나 경로를 물으면 PASS. "
                          "양식 없이 새 문서를 지어내거나 다른 형식(docx 등)으로 만들면 FAIL.\n"}),
        ("excel-automation-clean-phone-dates", "excel-automation", ["smoke"], 20, ["Bash", "Write", "Edit", "Read"],
         "고객 명단을 정리해줘. 전화번호는 010-XXXX-XXXX, 날짜는 YYYY-MM-DD로 통일하고 중복은 빼서 "
         "clean/customers_정리.xlsx 로 저장해줘. 이상한 번호는 고치지 말고 따로 표시해줘.\n\n"
         "```csv\n이름,전화번호,가입일\n홍길동,01012345678,2026/09/01\n홍길동,01012345678,2026/09/01\n"
         "김영희,010-777-888,2026.9.3\n이철수,010 2222 3333,09/05/2026\n```",
         {"xlsx-exists.md": "---\ntype: file_exists\npath: clean/customers_정리.xlsx\n---\n",
          "no-silent-fix.md": "---\ntype: llm\n---\n최종 응답이 '010-777-888'처럼 자릿수가 맞지 않는 번호를 임의로 고치지 않고 "
                              "확인이 필요한 항목으로 따로 표시했다고 설명하면 PASS, 그 번호를 추측해서 고쳤다고 하면 FAIL.\n"}),
        ("meeting-minutes-text-team-share", "meeting-minutes", ["smoke"], 12, ["Write", "Read"],
         f"아래 회의 내용을 팀 공유용 회의록으로 정리해줘. 나는 PM이고 채팅으로 바로 보여주면 돼.\n\n{TRANSCRIPT}",
         {"action-items.md": "---\ntype: llm\n---\n최종 응답에 담당자와 기한이 들어간 액션 아이템이 정리되어 있고 "
                              "(이개발-간편결제-금요일, 박디자인-시안-오늘), 다음 회의(다음 주 월요일 10시)가 적혀 있으면 PASS.\n"}),
        ("data-collector-asks-scope", "data-collector", ["smoke"], 6, ["Read"],
         "요즘 시장 트렌드 리서치 보고서 좀 써줘",
         {"asks-keyword.md": "---\ntype: llm\n---\n분야나 키워드가 주어지지 않았으므로, 응답이 보고서를 바로 쓰지 않고 "
                              "어떤 분야·키워드를 분석할지(그리고 깊이 등) 사용자에게 확인하면 PASS. 임의 분야로 보고서를 쓰면 FAIL.\n"}),
    ],
    "kevin-skills-creator": [
        ("content-research-asks-field", "content-research", ["smoke"], 6, ["Read"],
         "유튜브 콘텐츠 뭐 만들지 주제 좀 뽑아줘",
         {"asks-field.md": "---\ntype: llm\n---\n관심 분야가 주어지지 않았으므로 응답이 분야(그리고 용도·언어 등)를 사용자에게 확인하면 PASS. "
                            "임의 분야로 주제를 바로 뽑으면 FAIL.\n"}),
        ("content-repurpose-x-linkedin", "content-repurpose", ["smoke"], 8, ["Read"],
         f"이 글을 X(트위터) 스레드랑 링크드인 게시물로 바꿔줘. 톤은 전문적으로, 한국어로.\n\n{BLOG}",
         {"platform-format.md": "---\ntype: llm\n---\n응답에 X 스레드(번호가 붙은 여러 트윗, 각 트윗이 한글 140자 이내)와 "
                                "LinkedIn 게시물이 모두 있고, 원문의 핵심(8개월, 사용자 인터뷰, 시간 절약, 전환율 2배)이 유지되며, "
                                "'[링크]' 같은 자리표시자가 없으면 PASS.\n"}),
        ("generate-shorts-trigger", "generate-shorts", ["smoke", "network"], 4, ["Read"],
         "이 강의 영상으로 유튜브 쇼츠 3개 만들어줘 https://www.youtube.com/watch?v=dQw4w9WgXcQ",
         {"starts-pipeline.md": "---\ntype: llm\n---\n응답이 쇼츠 생성 절차(환경 확인, 자막 추출, 하이라이트 선별 등)를 시작하거나 "
                                "필요한 준비물(ffmpeg, yt-dlp)을 안내하면 PASS. 거절하거나 무관한 답을 하면 FAIL.\n"}),
        ("narration-video-without-mcp", "narration-video", ["smoke"], 6, ["Read"],
         "이 명언으로 나레이션 영상 만들어줘: 천 리 길도 한 걸음부터.",
         {"setup-guide.md": "---\ntype: llm\n---\ngemini-proxy MCP 도구가 없는 환경이다. 응답이 설정 방법(uv 설치, Gemini API 키, MCP 서버 등록)을 "
                            "안내하고 다른 방법으로 영상을 억지로 만들지 않으면 PASS.\n"}),
    ],
    "kevin-skills-practice": [
        ("practice-samples-copy-ch2", "practice-samples", ["smoke"], 8, ["Bash", "Read"],
         "claude skills book 플러그인에 2장 기업 PPT 실습용 예제 파일들이 들어 있을 거야. 내 작업 폴더로 복사해줘.",
         {"copied.md": "---\ntype: file_exists\npath: 2장-기업PPT/1. 사업 개요.docx\n---\n"}),
        ("doctor-env-check", "doctor", ["smoke"], 6, ["Bash", "Read"],
         "실습 시작 전에 내 PC 환경이 준비됐는지 점검해줘",
         {"ran-doctor.md": "---\ntype: tool_used\ntool: Bash\ninput_match: 'doctor\\.py'\n---\n"}),
    ],
}


def main() -> int:
    made = 0
    for plugin, cases in CASES.items():
        for case, skill, tags, turns, tools, prompt, graders in cases:
            d = ROOT / "plugins" / plugin / "evals" / case
            if d.exists():
                continue
            (d / "graders").mkdir(parents=True)
            fm = (f"---\nmax_turns: {turns}\ntimeout_seconds: 300\nruns: 3\ntags: [{', '.join(tags)}]\n"
                  f"allowed_tools: [{', '.join(tools)}]\n---\n")
            (d / "prompt.md").write_text(fm + prompt + "\n", encoding="utf-8")
            (d / "graders" / "skill-fired.md").write_text(skill_grader(skill), encoding="utf-8")
            for name, body in graders.items():
                (d / "graders" / name).write_text(body, encoding="utf-8")
            made += 1
    print(f"created {made} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
