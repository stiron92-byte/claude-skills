"""
콘텐츠 분석기
수집된 기사를 Claude API로 분석하여 콘텐츠 아이디어와 브리핑을 생성합니다.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("[오류] anthropic 패키지가 설치되지 않았습니다.")
    print("pip install anthropic 을 실행하세요.")
    sys.exit(1)

import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_analysis_prompt(articles: list[dict], config: dict) -> str:
    """기사 목록과 설정을 기반으로 분석 프롬프트를 생성합니다."""
    content_type = config.get("content_type", "general")
    custom_prompt = config.get("analysis_prompt", "")
    language = config.get("language", "ko")

    # 기사 요약 텍스트 구성
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"\n---\n"
        articles_text += f"[{i}] {article['title']}\n"
        articles_text += f"출처: {article['source']}\n"
        articles_text += f"날짜: {article.get('published', '알 수 없음')}\n"
        articles_text += f"요약: {article['summary']}\n"
        articles_text += f"링크: {article['link']}\n"

    # 용도별 기본 프롬프트
    type_prompts = {
        "youtube": (
            "위 뉴스에서 유튜브 영상 주제 5개를 뽑아주세요.\n"
            "각 주제에 대해 다음을 포함해주세요:\n"
            "- 영상 제목 (클릭을 유도하는)\n"
            "- 핵심 내용 요약 (3줄)\n"
            "- 썸네일 아이디어\n"
            "- 타겟 시청자\n"
            "- 예상 관심도 (높음/중간/낮음) + 이유"
        ),
        "blog": (
            "위 뉴스에서 블로그 글 주제 5개를 뽑아주세요.\n"
            "각 주제에 대해 다음을 포함해주세요:\n"
            "- 글 제목 (SEO 최적화)\n"
            "- SEO 키워드 3-5개\n"
            "- 글 구조 (소제목 목록)\n"
            "- 예상 독자\n"
            "- 참고할 원문 기사 번호"
        ),
        "newsletter": (
            "위 뉴스를 뉴스레터 형식으로 정리해주세요.\n"
            "포함할 내용:\n"
            "- 인사말 (2줄)\n"
            "- 이번 주 주요 뉴스 TOP 3 (각 3줄 요약)\n"
            "- 심화 분석 1개 (5-7줄)\n"
            "- 추천 링크 2-3개\n"
            "- 마무리 인사"
        ),
        "general": (
            "위 뉴스를 분석하여 다음을 제공해주세요:\n"
            "1. 주요 트렌드 요약 (3-5개)\n"
            "2. 콘텐츠 아이디어 5개 (제목 + 간단 설명)\n"
            "3. 주목할 키워드 5개\n"
            "4. 한줄 총평"
        ),
    }

    analysis_instruction = custom_prompt or type_prompts.get(content_type, type_prompts["general"])

    lang_instruction = ""
    if language == "ko":
        lang_instruction = "\n\n반드시 한국어로 작성해주세요."
    elif language == "en":
        lang_instruction = "\n\nPlease write in English."

    prompt = f"""다음은 최근 수집된 뉴스 기사 목록입니다:

{articles_text}

---

{analysis_instruction}{lang_instruction}
"""
    return prompt


def analyze_content(articles: list[dict], config: dict) -> str:
    """Claude API를 사용하여 기사를 분석합니다."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[오류] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print(".env 파일에 ANTHROPIC_API_KEY=your_key_here 를 추가하세요.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model = config.get("model", "claude-sonnet-4-20250514")
    max_tokens = config.get("max_tokens", 4096)

    prompt = build_analysis_prompt(articles, config)

    print("\nClaude에게 분석 요청 중...")
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    result = message.content[0].text
    print("분석 완료!")
    return result


def generate_calendar(articles: list[dict], config: dict) -> str:
    """3개월 콘텐츠 캘린더를 생성합니다."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[오류] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model = config.get("model", "claude-sonnet-4-20250514")
    content_type = config.get("content_type", "general")

    articles_text = ""
    for i, article in enumerate(articles[:20], 1):
        articles_text += f"[{i}] {article['title']} — {article['summary'][:100]}\n"

    prompt = f"""다음 뉴스 트렌드를 기반으로 향후 3개월 콘텐츠 캘린더를 만들어주세요.

최근 트렌드:
{articles_text}

콘텐츠 유형: {content_type}

요구사항:
- 주 2회 발행 기준 (총 24개 콘텐츠)
- 각 항목에 날짜, 제목, 핵심 키워드 포함
- 시즌/이벤트 고려
- 마크다운 표 형식으로 작성
- 한국어로 작성
"""

    print("\n콘텐츠 캘린더 생성 중...")
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def save_analysis(analysis: str, output_dir: str = "output", prefix: str = "briefing") -> str:
    """분석 결과를 마크다운 파일로 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"{prefix}_{timestamp}.md")

    header = f"# 콘텐츠 브리핑 — {datetime.now().strftime('%Y년 %m월 %d일')}\n\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + analysis)

    print(f"분석 결과 저장: {filepath}")
    return filepath


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="수집된 기사를 분석합니다.")
    parser.add_argument("articles_file", help="기사 JSON 파일 경로")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로")
    parser.add_argument("--calendar", action="store_true", help="콘텐츠 캘린더 생성")
    args = parser.parse_args()

    config = load_config(args.config)

    with open(args.articles_file, "r", encoding="utf-8") as f:
        articles = json.load(f)

    if args.calendar:
        calendar = generate_calendar(articles, config)
        save_analysis(calendar, prefix="calendar")
    else:
        analysis = analyze_content(articles, config)
        save_analysis(analysis)
