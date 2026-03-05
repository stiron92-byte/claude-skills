"""
data-collector 분석 엔진

모드1에서의 사용법:
  Claude가 web_search/WebFetch로 수집한 데이터를 collected_data.json으로 저장한 후,
  이 스크립트를 호출하여 분석한다. (네트워크 불필요, 로컬 파일 처리만)

  python analyzer.py <collected_data.json 경로> [keyword]

  분석 결과는 같은 디렉토리에 analysis_result.json으로 저장된다.
"""
import re
import sys
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger('data-collector.analyzer')


def analyze_keyword_frequency(data_items, keyword=None):
    """키워드 빈도 분석: 가장 많이 언급된 키워드/엔티티 추출"""
    text_pool = []
    for item in data_items:
        if isinstance(item, dict):
            text_pool.append(item.get('title', ''))
            text_pool.append(item.get('summary', ''))

    combined = ' '.join(text_pool)

    korean_words = re.findall(r'[가-힣]{2,}', combined)
    english_words = re.findall(r'[A-Za-z]{3,}', combined)

    stopwords_ko = {'것이', '하는', '있는', '위해', '대한', '통해', '이번', '지난', '올해', '관련'}
    stopwords_en = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'has', 'was', 'one', 'our', 'out', 'this', 'that', 'with', 'from', 'have', 'been'}

    korean_words = [w for w in korean_words if w not in stopwords_ko]
    english_words = [w.lower() for w in english_words if w.lower() not in stopwords_en]

    all_words = korean_words + english_words
    frequency = Counter(all_words)

    return {
        'top_keywords': frequency.most_common(20),
        'total_words': len(all_words),
        'unique_words': len(set(all_words))
    }


def analyze_temporal_classification(data_items):
    """시점별 분류: 과거/현재/미래"""
    now = datetime.now()
    past_cutoff = now - timedelta(days=90)

    classified = {
        'past': [],
        'current': [],
        'future': []
    }

    future_indicators = ['전망', '예측', '예상', '계획', '출시 예정', 'forecast', 'outlook', 'upcoming', 'expected', 'will']

    for item in data_items:
        if not isinstance(item, dict):
            continue

        text = (item.get('title', '') + ' ' + item.get('summary', '')).lower()

        if any(ind in text for ind in future_indicators):
            classified['future'].append(item)
            continue

        pub_date = item.get('published')
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).replace(tzinfo=None)

                if pub_date < past_cutoff:
                    classified['past'].append(item)
                else:
                    classified['current'].append(item)
            except (ValueError, TypeError):
                classified['current'].append(item)
        else:
            classified['current'].append(item)

    return classified


def analyze_sentiment(data_items):
    """센티먼트 판단: 긍정/부정/중립 논조 비율"""
    positive_words = [
        '성장', '상승', '호조', '개선', '증가', '긍정', '혁신', '돌파', '최고', '기대',
        'growth', 'rise', 'increase', 'positive', 'innovation', 'breakthrough', 'best', 'strong'
    ]
    negative_words = [
        '하락', '감소', '위기', '부진', '악화', '리스크', '우려', '둔화', '폭락', '실패',
        'decline', 'decrease', 'crisis', 'risk', 'concern', 'slowdown', 'fall', 'fail', 'weak'
    ]

    sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}

    for item in data_items:
        if not isinstance(item, dict):
            continue

        text = (item.get('title', '') + ' ' + item.get('summary', '')).lower()

        pos_score = sum(1 for w in positive_words if w in text)
        neg_score = sum(1 for w in negative_words if w in text)

        if pos_score > neg_score:
            sentiment_counts['positive'] += 1
        elif neg_score > pos_score:
            sentiment_counts['negative'] += 1
        else:
            sentiment_counts['neutral'] += 1

    total = sum(sentiment_counts.values()) or 1
    sentiment_ratio = {k: round(v / total * 100, 1) for k, v in sentiment_counts.items()}

    return {
        'counts': sentiment_counts,
        'ratio': sentiment_ratio,
        'dominant': max(sentiment_counts, key=sentiment_counts.get)
    }


def analyze_anomaly_detection(data_items):
    """이상 신호 탐지: 급격한 변화, 이례적 패턴"""
    anomalies = []

    date_counts = defaultdict(int)
    for item in data_items:
        if not isinstance(item, dict):
            continue
        pub_date = item.get('published')
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    date_key = pub_date[:10]
                else:
                    date_key = pub_date.strftime('%Y-%m-%d')
                date_counts[date_key] += 1
            except (ValueError, AttributeError):
                pass

    if date_counts:
        avg_count = sum(date_counts.values()) / len(date_counts)
        for date, count in date_counts.items():
            if count > avg_count * 2:
                anomalies.append({
                    'date': date,
                    'count': count,
                    'average': round(avg_count, 1),
                    'type': 'volume_spike',
                    'description': f'{date}에 평균({avg_count:.0f}건) 대비 {count}건으로 급증'
                })

    return anomalies


def run_analysis(collected_data, keyword, profile=None):
    """
    전체 분석 파이프라인 실행

    Args:
        collected_data: Claude가 수집하여 JSON으로 저장한 데이터 리스트
                       [{"source": "...", "status": "success", "data": [...]}, ...]
        keyword: 분석 키워드
        profile: domain profile dict (선택)
    """
    all_items = []
    for result in collected_data:
        if result.get('status') == 'success':
            data = result.get('data', [])
            if isinstance(data, list):
                all_items.extend(data)
            else:
                all_items.append(data)

    logger.info(f"분석 대상: {len(all_items)}건")

    analysis_results = {
        'keyword': keyword,
        'keyword_frequency': analyze_keyword_frequency(all_items, keyword),
        'temporal_classification': {
            k: v for k, v in analyze_temporal_classification(all_items).items()
        },
        'sentiment': analyze_sentiment(all_items),
        'anomalies': analyze_anomaly_detection(all_items),
        'total_items': len(all_items)
    }

    if profile and 'analysis' in profile:
        framework = profile['analysis'].get('framework', [])
        analysis_results['domain_framework'] = []
        for f in framework:
            analysis_results['domain_framework'].append({
                'name': f.get('name'),
                'method': f.get('method'),
                'description': f.get('description'),
                'applied': True
            })

    return analysis_results


def main():
    """
    CLI 진입점.
    사용법: python analyzer.py <collected_data.json> [keyword]
    결과: 같은 디렉토리에 analysis_result.json 저장
    """
    if len(sys.argv) < 2:
        print("사용법: python analyzer.py <collected_data.json 경로> [keyword]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    keyword = sys.argv[2] if len(sys.argv) > 2 else 'unknown'

    if not input_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        collected_data = json.load(f)

    results = run_analysis(collected_data, keyword)

    output_path = input_path.parent / 'analysis_result.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"분석 완료: {output_path}")
    print(f"  총 데이터: {results['total_items']}건")
    print(f"  키워드 TOP 3: {results['keyword_frequency']['top_keywords'][:3]}")
    print(f"  센티먼트: {results['sentiment']['ratio']}")


if __name__ == '__main__':
    main()
