#!/usr/bin/env python3
"""이메일 요약 생성 모듈.

분석 결과를 기반으로 수신자별 톤의 이메일 본문을 생성합니다.
- 임원용: 핵심 수치 + 결론 중심, 간결체
- 팀원용: 상세 데이터 + 액션 아이템 포함
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def generate_executive_email(analysis: dict) -> str:
    """임원용 간결한 이메일을 생성합니다."""
    summary = analysis.get("summary", {})
    period = analysis.get("period", {})
    top_items = analysis.get("top_items", [])
    change_rate = summary.get("revenue_change_rate", 0)

    arrow = "▲" if change_rate >= 0 else "▼"
    trend = "성장" if change_rate >= 0 else "감소"

    top_products = ""
    for i, item in enumerate(top_items[:3], 1):
        top_products += f"   {i}. {item['name']} ({item['revenue']:,}원)\n"

    email = f"""제목: [주간 보고] {period.get('start', '')} ~ {period.get('end', '')} 실적 요약

안녕하세요,

금주 주간 실적을 보고드립니다.

■ 핵심 지표
  - 총 매출: {summary.get('total_revenue', 0):,}원 (전주 대비 {arrow} {abs(change_rate)}%)
  - 총 판매량: {summary.get('total_quantity', 0):,}개
  - 일 평균 매출: {summary.get('avg_daily_revenue', 0):,}원

■ TOP 3 상품
{top_products}
■ 요약
  금주 매출은 전주 대비 {abs(change_rate)}% {trend}하였습니다.\
{' 지속적인 성장 모멘텀을 유지하고 있습니다.' if change_rate >= 0 else ' 원인 분석 및 대응 전략을 수립 중입니다.'}

상세 분석은 첨부된 PPT 보고서를 참고해주시기 바랍니다.

감사합니다.
"""
    return email.strip()


def generate_team_email(analysis: dict) -> str:
    """팀원용 상세 이메일을 생성합니다."""
    summary = analysis.get("summary", {})
    period = analysis.get("period", {})
    top_items = analysis.get("top_items", [])
    category = analysis.get("category", {})
    change_rate = summary.get("revenue_change_rate", 0)

    arrow = "▲" if change_rate >= 0 else "▼"

    # TOP 5 상품 목록
    top_section = ""
    for i, item in enumerate(top_items[:5], 1):
        top_section += f"   {i}. {item['name']}: {item['revenue']:,}원 ({item['quantity']:,}개)\n"

    # 카테고리별 매출
    cat_section = ""
    if category.get("names"):
        total = sum(category["revenue"])
        for name, rev in zip(category["names"], category["revenue"]):
            pct = (rev / total * 100) if total > 0 else 0
            cat_section += f"   - {name}: {rev:,}원 ({pct:.1f}%)\n"

    email = f"""제목: [주간 보고] {period.get('start', '')} ~ {period.get('end', '')} 상세 분석

팀원 여러분 안녕하세요,

금주 실적 상세 분석 결과를 공유합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 주간 실적 요약
  - 총 매출: {summary.get('total_revenue', 0):,}원 (전주 대비 {arrow} {abs(change_rate)}%)
  - 총 판매량: {summary.get('total_quantity', 0):,}개
  - 일 평균 매출: {summary.get('avg_daily_revenue', 0):,}원
  - 판매 상품 수: {summary.get('unique_products', 0)}종
  - 분석 기간: {summary.get('total_days', 0)}일

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 TOP 5 상품
{top_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 카테고리별 매출
{cat_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 다음 주 액션 아이템
   1. 매출 변동 원인 심층 분석 → 담당자 지정
   2. TOP 상품 재고 확인 및 발주 검토
   3. 저성과 카테고리 프로모션 전략 논의
   4. 주간 KPI 목표 재설정

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

상세 차트 및 분석은 첨부된 PPT를 참고해주세요.
문의사항은 언제든 공유해주시기 바랍니다.

감사합니다.
"""
    return email.strip()


def main():
    parser = argparse.ArgumentParser(description="이메일 요약 생성")
    parser.add_argument("--analysis", required=True, help="analysis.json 경로")
    parser.add_argument("--type", choices=["executive", "team", "both"],
                        default="both", help="이메일 유형")
    parser.add_argument("--output", default="output", help="출력 디렉토리")
    args = parser.parse_args()

    with open(args.analysis, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.type in ("executive", "both"):
        email = generate_executive_email(analysis)
        path = output_dir / "email_executive.md"
        path.write_text(email, encoding="utf-8")
        print(f"[임원용 이메일] 저장: {path}")

    if args.type in ("team", "both"):
        email = generate_team_email(analysis)
        path = output_dir / "email_team.md"
        path.write_text(email, encoding="utf-8")
        print(f"[팀원용 이메일] 저장: {path}")


if __name__ == "__main__":
    main()
