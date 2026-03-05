"""
data-collector 자동화 코드 생성기 (모드2)
GitHub Actions + Python 파이프라인 코드를 zip으로 생성한다.
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('data-collector.automation')


def build_automation_package(keyword, domain, config=None, output_dir=None):
    """자동화 파이프라인 패키지 생성"""
    if output_dir is None:
        output_dir = '/mnt/user-data/outputs'

    date_str = datetime.now().strftime('%Y%m%d')
    safe_keyword = keyword.replace(' ', '_').replace('/', '_')
    package_name = f"data_pipeline_{safe_keyword}_{date_str}"
    package_dir = os.path.join(output_dir, package_name)

    # 디렉토리 구조 생성
    os.makedirs(os.path.join(package_dir, '.github', 'workflows'), exist_ok=True)
    os.makedirs(os.path.join(package_dir, 'output'), exist_ok=True)

    # 1. 메인 수집 스크립트
    _write_main_script(package_dir, keyword, domain)

    # 2. config.yaml
    _write_config(package_dir, keyword, domain)

    # 3. GitHub Actions workflow
    _write_github_actions(package_dir)

    # 4. requirements.txt
    _write_requirements(package_dir)

    # 5. README.md
    _write_readme(package_dir, keyword, domain)

    # zip 생성
    zip_path = shutil.make_archive(package_dir, 'zip', output_dir, package_name)

    # 임시 디렉토리 정리
    shutil.rmtree(package_dir)

    logger.info(f"자동화 패키지 생성: {zip_path}")
    return zip_path


def _write_main_script(package_dir, keyword, domain):
    """메인 수집/분석 스크립트"""
    script = f'''#!/usr/bin/env python3
"""
{keyword} 데이터 수집 + 분석 파이프라인
자동 생성됨 - {datetime.now().strftime('%Y-%m-%d')}
"""
import os
import yaml
import feedparser
import requests
import json
import logging
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 2


def load_config():
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def fetch_with_retry(func, source_name, *args, **kwargs):
    import time
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = func(*args, **kwargs)
            logger.info(f"[{{source_name}}] 수집 성공")
            return {{"status": "success", "source": source_name, "data": result}}
        except Exception as e:
            if attempt < MAX_RETRIES:
                logger.warning(f"[{{source_name}}] 시도 {{attempt+1}} 실패: {{e}}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"[{{source_name}}] 최종 실패: {{e}}")
                return {{"status": "failed", "source": source_name, "reason": str(e)}}


def collect_rss(url, max_entries=10):
    feed = feedparser.parse(url)
    entries = []
    for entry in feed.entries[:max_entries]:
        entries.append({{
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'summary': entry.get('summary', ''),
        }})
    return entries


def collect_newsapi(api_key, query, language='ko'):
    url = 'https://newsapi.org/v2/everything'
    params = {{'q': query, 'language': language, 'pageSize': 10, 'sortBy': 'publishedAt', 'apiKey': api_key}}
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    return [
        {{'title': a.get('title', ''), 'link': a.get('url', ''), 'summary': a.get('description', '')}}
        for a in data.get('articles', [])
    ]


def generate_report(keyword, data_items, sources_info):
    now = datetime.now()
    lines = [
        f"# {{keyword}} 트렌드 리서치 보고서\\n",
        f"> 생성일: {{now.strftime('%Y-%m-%d')}}  ",
        f"> 분석 키워드: {{keyword}}  ",
        f"> 데이터 소스: {{', '.join(sources_info)}}\\n",
        "---\\n",
        "## 핵심 요약\\n",
    ]

    if data_items:
        lines.append(f"- 총 {{len(data_items)}}건의 데이터 수집됨\\n")
        lines.append("## 수집된 데이터\\n")
        for i, item in enumerate(data_items[:20], 1):
            lines.append(f"{{i}}. **{{item.get('title', 'N/A')}}**")
            if item.get('link'):
                lines.append(f"   - {{item['link']}}")
    else:
        lines.append("- 수집된 데이터 없음\\n")

    return '\\n'.join(lines)


def main():
    config = load_config()
    keyword = config.get('keyword', '{keyword}')

    all_data = []
    sources = []

    # RSS 수집
    for feed in config.get('rss_feeds', []):
        result = fetch_with_retry(collect_rss, feed.get('name', 'RSS'), feed['url'])
        if result['status'] == 'success':
            all_data.extend(result['data'])
            sources.append(result['source'])

    # NewsAPI (키가 있으면)
    newsapi_key = os.environ.get('NEWSAPI_KEY', config.get('api_keys', {{}}).get('newsapi', ''))
    if newsapi_key:
        result = fetch_with_retry(collect_newsapi, 'NewsAPI', newsapi_key, keyword)
        if result['status'] == 'success':
            all_data.extend(result['data'])
            sources.append('NewsAPI')

    # 보고서 생성
    report = generate_report(keyword, all_data, sources)

    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime('%Y%m%d')
    output_path = output_dir / f"{{keyword}}_report_{{date_str}}.md"
    output_path.write_text(report, encoding='utf-8')

    logger.info(f"보고서 저장: {{output_path}}")

    # Slack 알림 (webhook URL이 있으면)
    slack_webhook = os.environ.get('SLACK_WEBHOOK_URL', '')
    if slack_webhook:
        try:
            requests.post(slack_webhook, json={{
                'text': f"{{keyword}} 트렌드 보고서가 생성되었습니다. ({{len(all_data)}}건 수집)"
            }}, timeout=10)
            logger.info("Slack 알림 전송 완료")
        except Exception as e:
            logger.warning(f"Slack 알림 실패: {{e}}")


if __name__ == '__main__':
    main()
'''

    with open(os.path.join(package_dir, 'collect_and_report.py'), 'w', encoding='utf-8') as f:
        f.write(script)


def _write_config(package_dir, keyword, domain):
    """config.yaml 작성"""
    config = f"""# 데이터 수집 파이프라인 설정
keyword: "{keyword}"
domain: "{domain or 'general'}"

# RSS 피드 목록
rss_feeds:
  - name: "RSS Feed 1"
    url: ""  # RSS 피드 URL을 입력하세요

# API 키 (선택사항 - 없으면 무료 소스만 사용)
api_keys:
  newsapi: ""  # https://newsapi.org

# 보고서 설정
report:
  language: "ko"
  depth: "deep"
"""

    with open(os.path.join(package_dir, 'config.yaml'), 'w', encoding='utf-8') as f:
        f.write(config)


def _write_github_actions(package_dir):
    """GitHub Actions workflow 작성"""
    workflow = """name: Daily Data Collection

on:
  schedule:
    - cron: '0 9 * * *'  # 매일 오전 9시 (UTC)
  workflow_dispatch:  # 수동 실행 가능

jobs:
  collect:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run collection pipeline
        env:
          NEWSAPI_KEY: ${{ secrets.NEWSAPI_KEY }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: python collect_and_report.py

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: trend-report-${{ github.run_number }}
          path: output/*.md
          retention-days: 30

      - name: Commit report to repo
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add output/
          git diff --cached --quiet || git commit -m "chore: add daily trend report $(date +%Y-%m-%d)"
          git push
"""

    workflow_path = os.path.join(package_dir, '.github', 'workflows', 'daily_collect.yml')
    with open(workflow_path, 'w', encoding='utf-8') as f:
        f.write(workflow)


def _write_requirements(package_dir):
    """requirements.txt 작성"""
    requirements = """feedparser>=6.0.0
requests>=2.28.0
pyyaml>=6.0
"""

    with open(os.path.join(package_dir, 'requirements.txt'), 'w', encoding='utf-8') as f:
        f.write(requirements)


def _write_readme(package_dir, keyword, domain):
    """README.md 작성"""
    readme = f"""# {keyword} 데이터 수집 파이프라인

자동으로 {keyword} 관련 데이터를 수집하고 트렌드 보고서를 생성합니다.

## 설치

```bash
pip install -r requirements.txt
```

## 설정

1. `config.yaml`에서 RSS 피드 URL과 API 키를 설정하세요.
2. (선택) NewsAPI 키: https://newsapi.org 에서 발급

## 실행

```bash
python collect_and_report.py
```

보고서는 `output/` 폴더에 생성됩니다.

## GitHub Actions 자동화

1. 이 저장소를 GitHub에 push
2. Settings > Secrets에 환경변수 추가:
   - `NEWSAPI_KEY`: NewsAPI 키 (선택)
   - `SLACK_WEBHOOK_URL`: Slack 알림 URL (선택)
3. 매일 오전 9시(UTC)에 자동 실행됩니다.
4. Actions 탭에서 수동 실행도 가능합니다.

## 출력

- `output/{{keyword}}_report_YYYYMMDD.md` 형태로 보고서 생성
- GitHub Actions 사용 시 Artifacts에서도 다운로드 가능
"""

    with open(os.path.join(package_dir, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme)


if __name__ == '__main__':
    import sys
    keyword = sys.argv[1] if len(sys.argv) > 1 else 'AI'
    domain = sys.argv[2] if len(sys.argv) > 2 else 'tech'

    zip_path = build_automation_package(keyword, domain, output_dir='/tmp')
    print(f"패키지 생성: {zip_path}")
