"""
콘텐츠 리서치 메인 파이프라인
RSS 수집 → 분석 → 브리핑 생성을 한 번에 실행합니다.
"""

import argparse
import os
import sys
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv 없으면 환경변수 직접 사용

from rss_collector import load_config, collect_all_feeds, filter_recent, save_articles
from content_analyzer import analyze_content, generate_calendar, save_analysis


def run_pipeline(config_path: str = "config.yaml", calendar: bool = False):
    """전체 파이프라인을 실행합니다."""
    print("=" * 60)
    print("  콘텐츠 리서치 파이프라인 시작")
    print("=" * 60)

    # 1. 설정 로드
    config = load_config(config_path)
    print(f"\n설정 파일: {config_path}")

    # 2. RSS 수집
    print("\n[1/3] RSS 피드 수집 중...")
    articles = collect_all_feeds(config)

    if not articles:
        print("\n수집된 기사가 없습니다. config.yaml의 rss_feeds를 확인하세요.")
        sys.exit(0)

    # 3. 최근 기사 필터링
    filter_days = config.get("filter_days", 3)
    if filter_days:
        articles = filter_recent(articles, days=filter_days)
        print(f"\n최근 {filter_days}일 이내 기사: {len(articles)}개")

    # 4. 기사 저장
    articles_file = save_articles(articles)

    # 5. 콘텐츠 분석
    articles_data = [
        {
            "title": a.title,
            "link": a.link,
            "summary": a.summary,
            "published": a.published,
            "source": a.source,
        }
        for a in articles
    ]

    if calendar:
        print("\n[2/3] 콘텐츠 캘린더 생성 중...")
        result = generate_calendar(articles_data, config)
        briefing_file = save_analysis(result, prefix="calendar")
    else:
        print("\n[2/3] 콘텐츠 분석 중...")
        result = analyze_content(articles_data, config)
        briefing_file = save_analysis(result)

    # 6. 완료
    print("\n[3/3] 파이프라인 완료!")
    print(f"\n  수집 기사: {articles_file}")
    print(f"  브리핑: {briefing_file}")
    print("=" * 60)

    return {"articles_file": articles_file, "briefing_file": briefing_file}


def main():
    parser = argparse.ArgumentParser(
        description="콘텐츠 리서치 자동화 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py --setup             대화형 설정 마법사 실행
  python main.py                     전체 파이프라인 실행
  python main.py --calendar          콘텐츠 캘린더 생성
  python main.py --config my.yaml    커스텀 설정 파일 사용
        """,
    )
    parser.add_argument("--setup", action="store_true", help="대화형 설정 마법사 실행")
    parser.add_argument("--config", default="config.yaml", help="설정 파일 경로 (기본: config.yaml)")
    parser.add_argument("--calendar", action="store_true", help="3개월 콘텐츠 캘린더 생성")

    args = parser.parse_args()

    if args.setup:
        from setup_wizard import run_wizard
        run_wizard()
        return

    # config.yaml이 없으면 설정 마법사 안내
    if not Path(args.config).exists():
        print(f"[오류] 설정 파일을 찾을 수 없습니다: {args.config}")
        print("\n다음 중 하나를 실행하세요:")
        print("  python scripts/main.py --setup          # 대화형 설정 마법사")
        print("  cp templates/config.example.yaml config.yaml  # 템플릿 복사 후 수정")
        sys.exit(1)

    run_pipeline(config_path=args.config, calendar=args.calendar)


if __name__ == "__main__":
    main()
