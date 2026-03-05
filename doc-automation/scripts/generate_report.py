#!/usr/bin/env python3
"""주간 보고서 자동 생성 — 메인 파이프라인.

전체 프로세스를 한 번에 실행합니다:
1. 데이터 분석 + 차트 생성
2. PPT 보고서 생성
3. 요약 이메일 생성
"""

import argparse
import sys
from pathlib import Path

from analyze_data import load_data, analyze_sales_data, generate_charts
from create_pptx import create_presentation
from generate_email import generate_executive_email, generate_team_email


def main():
    parser = argparse.ArgumentParser(
        description="주간 보고서 자동 생성 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python generate_report.py --input samples/weekly_sales.csv
  python generate_report.py --input data.xlsx --output reports/
  python generate_report.py --input data.csv --template templates/brand.pptx
        """,
    )
    parser.add_argument("--input", required=True, help="CSV 또는 엑셀 파일 경로")
    parser.add_argument("--output", default="output", help="출력 디렉토리 (기본: output)")
    parser.add_argument("--template", default=None, help="브랜드 PPT 템플릿 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  주간 보고서 자동 생성 파이프라인")
    print("=" * 60)
    print(f"  입력: {args.input}")
    print(f"  출력: {args.output}/")
    print("=" * 60)

    # Step 1: 데이터 분석
    print("\n[STEP 1/3] 데이터 분석 및 차트 생성")
    print("-" * 40)
    df = load_data(str(input_path))
    print(f"  데이터 로드: {len(df)}행 x {len(df.columns)}열")

    analysis = analyze_sales_data(df)
    chart_paths = generate_charts(analysis, str(output_dir))
    analysis["chart_paths"] = chart_paths

    import json
    analysis_path = output_dir / "analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    summary = analysis["summary"]
    change = summary.get("revenue_change_rate", 0)
    arrow = "↑" if change >= 0 else "↓"
    print(f"  총 매출: {summary['total_revenue']:,}원 ({arrow} {abs(change)}%)")
    print(f"  차트 {len(chart_paths)}개 생성 완료")

    # Step 2: PPT 생성
    print(f"\n[STEP 2/3] PPT 보고서 생성")
    print("-" * 40)
    pptx_path = str(output_dir / "weekly_report.pptx")
    create_presentation(analysis, pptx_path, args.template)

    # Step 3: 이메일 요약
    print(f"\n[STEP 3/3] 요약 이메일 생성")
    print("-" * 40)

    exec_email = generate_executive_email(analysis)
    exec_path = output_dir / "email_executive.md"
    exec_path.write_text(exec_email, encoding="utf-8")
    print(f"  임원용 이메일: {exec_path}")

    team_email = generate_team_email(analysis)
    team_path = output_dir / "email_team.md"
    team_path.write_text(team_email, encoding="utf-8")
    print(f"  팀원용 이메일: {team_path}")

    # 완료 요약
    print("\n" + "=" * 60)
    print("  생성 완료!")
    print("=" * 60)
    print(f"  PPT 보고서  : {pptx_path}")
    print(f"  분석 데이터  : {analysis_path}")
    print(f"  차트 이미지  : {output_dir}/charts/ ({len(chart_paths)}개)")
    print(f"  임원용 이메일 : {exec_path}")
    print(f"  팀원용 이메일 : {team_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
