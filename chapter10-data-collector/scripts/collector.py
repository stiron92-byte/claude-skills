"""
data-collector 데이터 수집 엔진

========================================================
⚠️  이 파일은 모드2(자동화 패키지) 레퍼런스 코드입니다.
⚠️  모드1(즉시 실행)에서는 절대 실행하지 않습니다.
========================================================

모드1에서의 데이터 수집:
  → Claude의 web_search / WebFetch 도구를 사용한다.
  → 수집 결과를 collected_data.json으로 저장한다.
  → 이후 analyzer.py, report_generator.py가 JSON을 읽어 로컬에서 처리한다.

모드2에서의 데이터 수집:
  → 이 파일의 함수들이 automation_builder.py에 의해
    독립 실행 패키지에 포함된다.
  → 사용자 환경(로컬 PC, GitHub Actions)에서 실행되므로
    requests, feedparser 등 HTTP 라이브러리 사용이 가능하다.

컨테이너 환경 참고:
  Claude Code는 컨테이너 기반 Desktop에서 실행되며,
  컨테이너 내부에서 외부 네트워크 접근이 제한될 수 있다.
  따라서 모드1에서는 이 파일을 사용하지 않고,
  Claude의 내장 도구(web_search, WebFetch, curl)로 수집한다.
"""
import feedparser
import requests
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus

logger = logging.getLogger('data-collector.collector')


# ============================================================
# 아래 함수들은 모드2 자동화 패키지에서만 사용된다.
# 컨테이너 내부(모드1)에서는 호출하지 않는다.
# ============================================================

def collect_rss(url, max_entries=10, filter_days=7):
    """RSS 피드에서 데이터 수집 (모드2 전용 - 외부 네트워크 필요)"""
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        raise Exception(f"RSS 파싱 실패: {feed.bozo_exception}")

    cutoff_date = datetime.now() - timedelta(days=filter_days)
    entries = []

    for entry in feed.entries[:max_entries]:
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published = datetime(*entry.updated_parsed[:6])

        if published and published < cutoff_date:
            continue

        entries.append({
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'summary': entry.get('summary', entry.get('description', '')),
            'published': published.isoformat() if published else None,
            'source_type': 'rss'
        })

    return entries


def collect_newsapi(api_key, query, language='ko', page_size=10):
    """NewsAPI에서 뉴스 수집 (모드2 전용 - 외부 네트워크 필요)"""
    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': query,
        'language': language,
        'pageSize': page_size,
        'sortBy': 'publishedAt',
        'apiKey': api_key
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get('status') != 'ok':
        raise Exception(f"NewsAPI 오류: {data.get('message', 'unknown')}")

    entries = []
    for article in data.get('articles', []):
        entries.append({
            'title': article.get('title', ''),
            'link': article.get('url', ''),
            'summary': article.get('description', ''),
            'published': article.get('publishedAt', ''),
            'source_name': article.get('source', {}).get('name', ''),
            'source_type': 'newsapi'
        })

    return entries


def collect_fred(api_key, series_ids=None):
    """FRED API에서 경제지표 수집 (모드2 전용 - 외부 네트워크 필요)"""
    if series_ids is None:
        series_ids = ['FEDFUNDS', 'CPIAUCSL', 'UNRATE', 'GDP']

    entries = []
    base_url = 'https://api.stlouisfed.org/fred/series/observations'

    for series_id in series_ids:
        params = {
            'series_id': series_id,
            'api_key': api_key,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 12
        }

        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        observations = data.get('observations', [])
        entries.append({
            'series_id': series_id,
            'data': [
                {'date': obs['date'], 'value': obs['value']}
                for obs in observations
                if obs.get('value') != '.'
            ],
            'source_type': 'fred'
        })

    return entries


def collect_youtube(api_key, query, max_results=10):
    """YouTube Data API에서 검색 결과 수집 (모드2 전용 - 외부 네트워크 필요)"""
    url = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'maxResults': max_results,
        'order': 'date',
        'key': api_key
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    entries = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        video_id = item.get('id', {}).get('videoId', '')
        entries.append({
            'title': snippet.get('title', ''),
            'link': f'https://www.youtube.com/watch?v={video_id}' if video_id else '',
            'summary': snippet.get('description', ''),
            'published': snippet.get('publishedAt', ''),
            'channel': snippet.get('channelTitle', ''),
            'source_type': 'youtube'
        })

    return entries


def collect_steam(api_key, keyword=None):
    """Steam Web API에서 게임 정보 수집 (모드2 전용 - 외부 네트워크 필요)"""
    url = 'https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/'
    params = {'key': api_key}

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    entries = []
    ranks = data.get('response', {}).get('ranks', [])
    for rank in ranks[:20]:
        entries.append({
            'appid': rank.get('appid'),
            'concurrent_in_game': rank.get('concurrent_in_game', 0),
            'peak_in_game': rank.get('peak_in_game', 0),
            'source_type': 'steam'
        })

    return entries


def collect_data_go_kr(api_key, params=None):
    """공공데이터포털 API에서 데이터 수집 (모드2 전용 - 외부 네트워크 필요)"""
    url = 'http://openapi.molit.go.kr/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev'

    if params is None:
        now = datetime.now()
        params = {
            'serviceKey': api_key,
            'LAWD_CD': '11680',
            'DEAL_YMD': now.strftime('%Y%m'),
            'pageNo': '1',
            'numOfRows': '20'
        }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.text)

    entries = []
    items = root.findall('.//item')
    for item in items:
        entry = {}
        for child in item:
            entry[child.tag] = child.text
        entry['source_type'] = 'data_go_kr'
        entries.append(entry)

    return entries
