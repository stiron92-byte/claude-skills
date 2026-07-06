"""
data-collector 보고서 생성기

모드1에서의 사용법:
  Claude가 수집한 데이터(collected_data.json)와
  분석 결과(analysis_result.json)를 기반으로 보고서를 생성한다.
  (네트워크 불필요, 로컬 파일 처리만)

  python report_generator.py <collected_data.json> <analysis_result.json> [keyword] [domain]

  보고서는 같은 디렉토리에 {keyword}_trend_report_{YYYYMMDD}.md로 저장된다.
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('data-collector.report')


def generate_report(keyword, analysis_results, collected_data, profile=None, config=None):
    """트렌드 리서치 보고서 생성"""
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')

    # 소스 정보 정리
    used_sources = []
    excluded_sources = []
    for r in collected_data:
        status = r.get('status', 'unknown')
        source = r.get('source', 'unknown')
        if status == 'success':
            used_sources.append(source)
        elif status in ('failed', 'skipped'):
            excluded_sources.append(f"{source} ({r.get('reason', '알 수 없는 오류')})")

    # 분석 결과 추출
    keyword_freq = analysis_results.get('keyword_frequency', {})
    temporal = analysis_results.get('temporal_classification', {})
    sentiment = analysis_results.get('sentiment', {})
    anomalies = analysis_results.get('anomalies', [])
    total_items = analysis_results.get('total_items', 0)

    report_lines = []

    # 헤더
    report_lines.append(f"# {keyword} 트렌드 리서치 보고서\n")
    report_lines.append(f"> 생성일: {date_str}  ")
    report_lines.append(f"> 분석 키워드: {keyword}  ")
    report_lines.append(f"> 데이터 소스: {', '.join(used_sources) if used_sources else '없음'}  ")
    if excluded_sources:
        report_lines.append(f"> 제외된 소스: {', '.join(excluded_sources)}")
    report_lines.append("")

    if total_items < 3:
        report_lines.append("> **데이터 불충분** - 수집된 데이터가 3건 미만입니다. 키워드를 조정해보세요.\n")

    report_lines.append("---\n")

    # 핵심 요약
    report_lines.append("## 핵심 요약 (Executive Summary)\n")
    top_kw = keyword_freq.get('top_keywords', [])[:5]
    sentiment_ratio = sentiment.get('ratio', {})
    dominant = sentiment.get('dominant', 'neutral')

    if top_kw:
        top_words = ', '.join([f"{w[0]}({w[1]}회)" for w in top_kw[:3]])
        report_lines.append(f"- 가장 많이 언급된 키워드: {top_words}")

    report_lines.append(f"- 전체 논조: {_sentiment_label(dominant)} "
                       f"(긍정 {sentiment_ratio.get('positive', 0)}% / "
                       f"부정 {sentiment_ratio.get('negative', 0)}% / "
                       f"중립 {sentiment_ratio.get('neutral', 0)}%)")

    if anomalies:
        report_lines.append(f"- 이상 신호 {len(anomalies)}건 탐지됨")

    report_lines.append(f"- 총 수집 데이터: {total_items}건")
    report_lines.append("")
    report_lines.append("---\n")

    # 1. 과거 동향
    report_lines.append("## 1. 과거 동향 (Past Trends)")
    report_lines.append("**기간: 최근 6개월 ~ 1년**\n")

    past_items = temporal.get('past', [])
    if past_items:
        report_lines.append("### 주요 흐름\n")
        for item in past_items[:5]:
            title = item.get('title', '제목 없음')
            pub = item.get('published', '')[:10] if item.get('published') else ''
            report_lines.append(f"- **{title}** ({pub})")

        report_lines.append("\n### 주요 이벤트 타임라인\n")
        report_lines.append("| 시기 | 이벤트 | 영향 |")
        report_lines.append("|------|--------|------|")
        for item in past_items[:3]:
            pub = item.get('published', '')[:7] if item.get('published') else 'N/A'
            title = item.get('title', '이벤트')
            report_lines.append(f"| {pub} | {title} | 분석 필요 |")
    else:
        report_lines.append("- 해당 기간 데이터가 부족합니다.\n")

    report_lines.append("")
    report_lines.append("---\n")

    # 2. 현재 트렌드
    report_lines.append("## 2. 현재 트렌드 (Current Trends)")
    report_lines.append("**기간: 최근 1~3개월**\n")

    current_items = temporal.get('current', [])
    if current_items:
        report_lines.append("### 지금 가장 뜨는 것\n")
        for i, item in enumerate(current_items[:5], 1):
            title = item.get('title', '제목 없음')
            summary = item.get('summary', '')[:100]
            report_lines.append(f"{i}. **{title}**")
            if summary:
                report_lines.append(f"   - {summary}")

        report_lines.append("\n### 데이터가 말하는 것\n")
        if top_kw:
            report_lines.append(f"- 상위 키워드 TOP 10: {', '.join([w[0] for w in top_kw[:10]])}")
        report_lines.append(f"- 현재 기간 데이터: {len(current_items)}건 수집됨")
    else:
        report_lines.append("- 해당 기간 데이터가 부족합니다.\n")

    report_lines.append("")
    report_lines.append("---\n")

    # 3. 향후 전망
    report_lines.append("## 3. 향후 전망 (Future Outlook)")
    report_lines.append("**기간: 향후 3~6개월**\n")

    future_items = temporal.get('future', [])
    if future_items:
        report_lines.append("### 예측\n")
        for i, item in enumerate(future_items[:5], 1):
            title = item.get('title', '제목 없음')
            report_lines.append(f"{i}. **{title}**")
            summary = item.get('summary', '')[:100]
            if summary:
                report_lines.append(f"   - 근거: {summary}")
    else:
        report_lines.append("- 전망 관련 데이터를 추가 수집하여 업데이트가 필요합니다.\n")

    if anomalies:
        report_lines.append("\n### 주목할 신호 (Watch List)\n")
        for a in anomalies:
            report_lines.append(f"- {a.get('description', '이상 신호 감지')}")

    report_lines.append("")
    report_lines.append("---\n")

    # 4. 분야별 심화 분석
    if profile and 'report' in profile:
        highlight_sections = profile['report'].get('highlight_sections', [])
        if highlight_sections:
            report_lines.append("## 4. 분야별 심화 분석\n")
            for section in highlight_sections:
                report_lines.append(f"### {section}\n")
                report_lines.append("- (수집된 데이터를 기반으로 분석 필요)\n")
            report_lines.append("---\n")

    # 참고 자료 및 출처
    report_lines.append("## 참고 자료 및 출처\n")
    report_lines.append("| 출처 | 제목 | 날짜 | URL |")
    report_lines.append("|------|------|------|-----|")

    all_items = []
    for r in collected_data:
        if r.get('status') == 'success':
            data = r.get('data', [])
            source = r.get('source', '')
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        item['_source'] = source
                        all_items.append(item)

    for item in all_items[:20]:
        source = item.get('_source', item.get('source_name', ''))
        title = item.get('title', 'N/A')[:50]
        pub = item.get('published', 'N/A')[:10] if item.get('published') else 'N/A'
        link = item.get('link', '')
        report_lines.append(f"| {source} | {title} | {pub} | {link} |")

    report_lines.append("")
    report_lines.append("---\n")

    # 분석 메타데이터
    report_lines.append("## 분석 메타데이터\n")
    report_lines.append(f"- 총 수집 데이터: {total_items}건")
    report_lines.append(f"- 사용된 소스: {', '.join(used_sources) if used_sources else '없음'}")
    report_lines.append(f"- 분석 시점: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    if excluded_sources:
        report_lines.append(f"- 제외된 소스: {', '.join(excluded_sources)}")

    return '\n'.join(report_lines)


def _sentiment_label(dominant):
    """센티먼트 라벨 변환"""
    labels = {
        'positive': '긍정적',
        'negative': '부정적',
        'neutral': '중립적'
    }
    return labels.get(dominant, '중립적')


def main():
    """
    CLI 진입점.
    사용법: python report_generator.py <collected_data.json> <analysis_result.json> [keyword] [domain_profile.yaml]
    결과: 같은 디렉토리에 {keyword}_trend_report_{YYYYMMDD}.md 저장
    """
    if len(sys.argv) < 3:
        print("사용법: python report_generator.py <collected_data.json> <analysis_result.json> [keyword] [domain_profile.yaml]")
        sys.exit(1)

    collected_path = Path(sys.argv[1])
    analysis_path = Path(sys.argv[2])
    keyword = sys.argv[3] if len(sys.argv) > 3 else 'unknown'

    # domain profile 로드 (선택)
    profile = None
    if len(sys.argv) > 4:
        profile_path = Path(sys.argv[4])
        if profile_path.exists():
            import yaml
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = yaml.safe_load(f)

    if not collected_path.exists():
        print(f"오류: 수집 데이터 파일 없음: {collected_path}")
        sys.exit(1)
    if not analysis_path.exists():
        print(f"오류: 분석 결과 파일 없음: {analysis_path}")
        sys.exit(1)

    with open(collected_path, 'r', encoding='utf-8') as f:
        collected_data = json.load(f)
    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis_results = json.load(f)

    report = generate_report(keyword, analysis_results, collected_data, profile)

    # 저장
    date_str = datetime.now().strftime('%Y%m%d')
    safe_keyword = keyword.replace(' ', '_').replace('/', '_')
    filename = f"{safe_keyword}_trend_report_{date_str}.md"
    output_path = collected_path.parent / filename

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"보고서 생성 완료: {output_path}")


if __name__ == '__main__':
    main()
