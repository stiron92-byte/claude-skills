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

from analyze_data import (
    load_tabular_data, load_document_text, analyze_sales_data,
    analyze_document, generate_charts, detect_file_type,
)
from create_pptx import create_presentation
from generate_email import generate_executive_email, generate_team_email
from style_config import default_style, from_template_info


def main():
    parser = argparse.ArgumentParser(
        description="주간 보고서 자동 생성 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python generate_report.py --input weekly_sales.csv
  python generate_report.py --input data.xlsx --output reports/
  python generate_report.py --input data.csv --template templates/brand.pptx
  python generate_report.py --input document.hwpx

HWPX 양식 채우기(--hwpx-template)는 v2에서 hwpx-editor 스킬로 옮겼다.
        """,
    )
    parser.add_argument("--input", required=True, help="입력 파일 경로 (CSV, 엑셀, PDF, HWPX 등)")
    parser.add_argument("--output", default="output", help="출력 디렉토리 (기본: output)")
    parser.add_argument("--template", default=None, help="브랜드 PPT 템플릿 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_type = detect_file_type(args.input)

    print("=" * 60)
    print("  보고서 자동 생성 파이프라인")
    print("=" * 60)
    print(f"  입력: {args.input} ({file_type})")
    print(f"  출력: {args.output}/")
    if args.template:
        print(f"  PPT 템플릿: {args.template}")
    print("=" * 60)

    # Step 0: PPT 템플릿 분석 (템플릿이 있는 경우)
    style = default_style()
    if args.template:
        print("\n[STEP 0] PPT 템플릿 분석")
        print("-" * 40)
        from template_analyzer import analyze_template, print_template_summary
        info = analyze_template(args.template)
        style = from_template_info(info)
        print_template_summary(info)

    # Step 1: 데이터 분석
    import json
    print("\n[STEP 1/3] 데이터 분석 및 차트 생성")
    print("-" * 40)

    if file_type == "tabular":
        df = load_tabular_data(str(input_path))
        print(f"  데이터 로드: {len(df)}행 x {len(df.columns)}열")
        analysis = analyze_sales_data(df)
        chart_paths = generate_charts(analysis, str(output_dir))
        analysis["chart_paths"] = chart_paths

        summary = analysis["summary"]
        if "total_revenue" in summary:
            change = summary.get("revenue_change_rate", 0)
            arrow = "↑" if change >= 0 else "↓"
            print(f"  총 매출: {summary['total_revenue']:,}원 ({arrow} {abs(change)}%)")
        print(f"  차트 {len(chart_paths)}개 생성 완료")
    else:
        text = load_document_text(str(input_path))
        print(f"  텍스트 추출: {len(text):,}자")
        analysis = analyze_document(text, str(input_path))
        analysis["chart_paths"] = []

        summary = analysis["summary"]
        print(f"  {summary['total_lines']}줄, {summary['total_words']}단어")

    analysis_path = output_dir / "analysis.json"
    # full_text는 별도 파일로 분리
    full_text = analysis.pop("full_text", None)
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    if full_text:
        text_file = output_dir / "extracted_text.txt"
        text_file.write_text(full_text, encoding="utf-8")
        analysis["full_text_path"] = str(text_file)

    # Step 2: PPT 생성
    print(f"\n[STEP 2/3] PPT 보고서 생성")
    print("-" * 40)
    pptx_path = str(output_dir / "weekly_report.pptx")
    create_presentation(analysis, pptx_path, args.template, style)

    # HWPX 양식 채우기는 v2에서 hwpx-editor 스킬로 옮겼다. 이 파이프라인은 PPT·이메일만 만든다.

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
    if analysis.get("chart_paths"):
        print(f"  차트 이미지  : {output_dir}/charts/ ({len(analysis['chart_paths'])}개)")
    print(f"  임원용 이메일 : {exec_path}")
    print(f"  팀원용 이메일 : {team_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
