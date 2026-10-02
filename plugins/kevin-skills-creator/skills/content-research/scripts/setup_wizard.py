"""
대화형 설정 마법사
사용자에게 질문하여 config.yaml과 .env를 자동 생성합니다.
CLI에서 직접 실행하거나 Claude 스킬이 프로그래밍적으로 호출할 수 있습니다.
"""

import os
import yaml

# 분야별 추천 RSS 피드
RECOMMENDED_FEEDS = {
    "tech": [
        "https://hnrss.org/frontpage",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "cooking": [
        "https://www.seriouseats.com/feed",
        "https://www.bonappetit.com/feed/rss",
        "https://www.maangchi.com/feed",
    ],
    "finance": [
        "https://feeds.bloomberg.com/markets/news.rss",
    ],
    "travel": [],
    "korean-it": [
        "https://news.hada.io/rss",
        "https://yozm.wishket.com/magazine/feed/",
    ],
}

CONTENT_TYPES = ["youtube", "blog", "newsletter", "general"]


def ask(question: str, default: str = "") -> str:
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "
    answer = input(prompt).strip()
    return answer if answer else default


def ask_choice(question: str, choices: list[str], default: str = "") -> str:
    print(f"\n{question}")
    for i, choice in enumerate(choices, 1):
        marker = " (기본)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")
    while True:
        answer = input(f"선택 [1-{len(choices)}]: ").strip()
        if not answer and default:
            return default
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            if answer in choices:
                return answer
        print("올바른 번호를 입력해주세요.")


def ask_yes_no(question: str, default: bool = False) -> bool:
    yn = "Y/n" if default else "y/N"
    answer = input(f"{question} [{yn}]: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes", "예", "네")


def run_wizard(output_dir: str = ".") -> dict:
    """대화형 설정 마법사를 실행합니다."""
    print("=" * 50)
    print("  콘텐츠 리서치 설정 마법사")
    print("=" * 50)

    # 1. 관심 분야
    print("\n--- 1/4 관심 분야 ---")
    topic = ask("관심 분야를 입력하세요 (예: tech, cooking, finance, travel, korean-it)", "tech")

    # 2. RSS 피드
    print("\n--- 2/4 RSS 피드 ---")
    feeds = []
    recommended = RECOMMENDED_FEEDS.get(topic, [])
    if recommended:
        print(f"\n'{topic}' 분야 추천 RSS 피드:")
        for feed in recommended:
            print(f"  - {feed}")
        if ask_yes_no("추천 피드를 사용하시겠습니까?", default=True):
            feeds = recommended.copy()

    print("\n추가할 RSS 피드 URL을 입력하세요 (빈 줄로 종료):")
    while True:
        url = input("  RSS URL: ").strip()
        if not url:
            break
        feeds.append(url)

    if not feeds:
        print("[경고] RSS 피드가 없습니다. 기본 피드(Hacker News)를 추가합니다.")
        feeds = ["https://hnrss.org/frontpage"]

    # 3. 콘텐츠 용도
    print("\n--- 3/4 콘텐츠 용도 ---")
    content_type = ask_choice(
        "콘텐츠 용도를 선택하세요:",
        CONTENT_TYPES,
        default="general",
    )

    # 4. 출력 언어
    print("\n--- 4/4 출력 언어 ---")
    language = ask_choice(
        "브리핑 출력 언어를 선택하세요:",
        ["한국어", "영어"],
        default="한국어",
    )
    lang_code = "ko" if language == "한국어" else "en"

    # config.yaml 생성
    config = generate_config(feeds, content_type, lang_code)

    config_path = os.path.join(output_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"\n[완료] config.yaml 생성: {config_path}")

    # .env 생성
    env_path = os.path.join(output_dir, ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("# https://console.anthropic.com/ 에서 API 키 발급\n")
        f.write("ANTHROPIC_API_KEY=your_api_key_here\n")
    print(f"[완료] .env 생성: {env_path}")
    print("\n⚠️  .env 파일을 열어 ANTHROPIC_API_KEY를 입력해주세요!")
    print("설정 완료. 'python scripts/main.py'로 실행하세요.")

    return config


def generate_config(
    feeds: list[str],
    content_type: str = "general",
    language: str = "ko",
) -> dict:
    """config 딕셔너리를 생성합니다."""
    return {
        "rss_feeds": feeds,
        "max_entries_per_feed": 10,
        "filter_days": 3,
        "content_type": content_type,
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "language": language,
        "analysis_prompt": "",
    }


def generate_config_file(
    feeds: list[str],
    content_type: str = "general",
    language: str = "ko",
    output_dir: str = ".",
) -> str:
    """프로그래밍 방식으로 config.yaml을 생성합니다. (Claude 스킬이 호출)"""
    config = generate_config(feeds, content_type, language)

    os.makedirs(output_dir, exist_ok=True)
    config_path = os.path.join(output_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return config_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="콘텐츠 리서치 설정 마법사")
    parser.add_argument("--output", default=".", help="설정 파일 출력 디렉토리")
    args = parser.parse_args()

    run_wizard(output_dir=args.output)
