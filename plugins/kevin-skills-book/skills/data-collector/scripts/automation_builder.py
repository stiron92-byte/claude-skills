"""
data-collector 자동화 코드 생성기 (모드2)
GitHub Actions + Python 파이프라인 코드를 zip으로 생성한다.

SKILL.md Step 6에 정의된 필수 9개 파일을 모두 생성한다:
  1. run_pipeline.py         — 전체 파이프라인 엔트리포인트
  2. collector.py            — RSS/API 데이터 수집
  3. analyzer.py             — 키워드/센티먼트/시점 분석
  4. report_generator.py     — Markdown 보고서 생성
  5. slack_notifier.py       — Slack Webhook 알림 (환경변수 우선, config 폴백)
  6. config.yaml             — 설정 (webhook_url은 반드시 빈 문자열)
  7. requirements.txt        — Python 의존성
  8. README.md               — 설치/실행 가이드
  9. .github/workflows/daily_collect.yml — GitHub Actions 워크플로
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('data-collector.automation')

# 이 스킬 디렉토리 기준으로 templates 폴더 위치
SKILL_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = SKILL_DIR / 'templates'


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
    os.makedirs(os.path.join(package_dir, 'reports'), exist_ok=True)

    # 필수 9개 파일 생성
    _write_run_pipeline(package_dir, keyword)
    _write_collector(package_dir, keyword, domain)
    _write_analyzer(package_dir)
    _write_report_generator(package_dir)
    _write_slack_notifier(package_dir)
    _write_config(package_dir, keyword, domain)
    _write_requirements(package_dir)
    _write_readme(package_dir, keyword, domain)
    _write_github_actions(package_dir, keyword)

    # 생성된 파일 검증
    required_files = [
        'run_pipeline.py', 'collector.py', 'analyzer.py',
        'report_generator.py', 'slack_notifier.py',
        'config.yaml', 'requirements.txt', 'README.md',
        os.path.join('.github', 'workflows', 'daily_collect.yml'),
    ]
    for f in required_files:
        fpath = os.path.join(package_dir, f)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"필수 파일 누락: {f}")
    logger.info(f"필수 파일 검증 완료: {len(required_files)}개 모두 존재")

    # zip 생성
    zip_path = shutil.make_archive(package_dir, 'zip', output_dir, package_name)

    # 임시 디렉토리 정리
    shutil.rmtree(package_dir)

    logger.info(f"자동화 패키지 생성: {zip_path}")
    return zip_path


def _write_run_pipeline(package_dir, keyword):
    """전체 파이프라인 엔트리포인트"""
    script = '''#!/usr/bin/env python3
"""
데이터 수집 파이프라인 엔트리포인트
수집 → 분석 → 보고서 생성 → Slack 알림을 순차 실행한다.
사용법: python run_pipeline.py [config.yaml 경로]
"""
import sys
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    start = time.time()

    logger.info("=" * 60)
    logger.info("트렌드 분석 파이프라인 시작")
    logger.info("=" * 60)

    # Step 1: 수집
    logger.info("[1/4] 데이터 수집...")
    from collector import load_config, run_collection
    import json

    config = load_config(config_path)
    output_dir = Path(config.get("output", {}).get("dir", "./reports"))
    output_dir.mkdir(parents=True, exist_ok=True)

    results = run_collection(config)
    collected_path = output_dir / "collected_data.json"
    with open(collected_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = sum(len(r.get("data", [])) for r in results if r.get("status") == "success")
    logger.info(f"  수집 완료: {total}건")

    # Step 2: 분석
    logger.info("[2/4] 분석...")
    from analyzer import run as run_analysis
    keyword = config.get("keyword", "unknown")
    analysis_path = run_analysis(str(collected_path), keyword)

    # Step 3: 보고서 생성
    logger.info("[3/4] 보고서 생성...")
    from report_generator import generate
    report_path, _ = generate(str(collected_path), analysis_path, keyword)
    logger.info(f"  보고서: {report_path}")

    # Step 4: Slack 알림
    logger.info("[4/4] Slack 알림...")
    from slack_notifier import send_notification
    slack_ok = send_notification(analysis_path, config_path)
    logger.info(f"  Slack: {'성공' if slack_ok else '실패 또는 비활성화'}")

    elapsed = time.time() - start
    logger.info(f"파이프라인 완료 ({elapsed:.1f}초)")


if __name__ == "__main__":
    main()
'''
    with open(os.path.join(package_dir, 'run_pipeline.py'), 'w', encoding='utf-8') as f:
        f.write(script)


def _write_collector(package_dir, keyword, domain):
    """데이터 수집 스크립트"""
    script = '''"""
데이터 수집기 — RSS/API에서 데이터를 수집한다.
"""
import json
import logging
import os
import sys
from pathlib import Path

import feedparser
import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_rss(sources):
    results = []
    for src in sources:
        if not src.get("enabled", True):
            continue
        name, url = src["name"], src["url"]
        if not url:
            continue
        logger.info(f"RSS 수집: {name}")
        try:
            feed = feedparser.parse(url)
            items = [
                {"title": e.get("title", ""), "link": e.get("link", ""),
                 "summary": e.get("summary", "")[:300], "published": e.get("published", ""),
                 "source_type": "rss"}
                for e in feed.entries[:20]
            ]
            results.append({"source": f"RSS - {name}", "status": "success", "data": items})
            logger.info(f"  → {len(items)}건")
        except Exception as e:
            logger.warning(f"  → 실패: {e}")
            results.append({"source": f"RSS - {name}", "status": "failed", "reason": str(e), "data": []})
    return results


def collect_newsapi(api_config, keywords):
    key = os.environ.get("NEWSAPI_KEY") or api_config.get("key", "")
    if not key:
        return [{"source": "NewsAPI", "status": "skipped", "reason": "API 키 미설정", "data": []}]

    query = " OR ".join(keywords[:5])
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize=20&apiKey={key}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        items = [
            {"title": a.get("title", ""), "link": a.get("url", ""),
             "summary": (a.get("description") or "")[:300],
             "published": (a.get("publishedAt") or "")[:10], "source_type": "api"}
            for a in resp.json().get("articles", [])
        ]
        return [{"source": "NewsAPI", "status": "success", "data": items}]
    except Exception as e:
        return [{"source": "NewsAPI", "status": "failed", "reason": str(e), "data": []}]


def run_collection(config):
    keyword = config.get("keyword", "unknown")
    keywords = config.get("keyword_expansion", [keyword])
    if keyword not in keywords:
        keywords.append(keyword)

    all_results = []
    all_results.extend(collect_rss(config.get("sources", {}).get("rss", [])))
    newsapi_config = config.get("sources", {}).get("api", {}).get("newsapi", {})
    all_results.extend(collect_newsapi(newsapi_config, keywords))
    return all_results


if __name__ == "__main__":
    config = load_config(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
    results = run_collection(config)
    total = sum(len(r.get("data", [])) for r in results if r["status"] == "success")
    print(f"수집 완료: {total}건")
'''
    with open(os.path.join(package_dir, 'collector.py'), 'w', encoding='utf-8') as f:
        f.write(script)


def _write_analyzer(package_dir):
    """분석 스크립트"""
    script = '''"""
데이터 분석기 — 키워드 빈도, 센티먼트, 시점 분류, 이상 신호를 추출한다.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def analyze_keyword_frequency(items):
    text = " ".join(i.get("title", "") + " " + i.get("summary", "") for i in items)
    korean = re.findall(r"[가-힣]{2,}", text)
    english = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", text)]
    stopwords = {"것이", "하는", "있는", "위해", "대한", "통해", "이번", "지난", "올해",
                 "the", "and", "for", "are", "but", "not", "this", "that", "with", "from", "have"}
    words = [w for w in korean + english if w not in stopwords]
    return {"top_keywords": Counter(words).most_common(20), "total": len(words)}


def analyze_temporal(items):
    now = datetime.now()
    cutoff = now - timedelta(days=90)
    future_words = ["전망", "예측", "예상", "forecast", "outlook", "expected", "will"]
    classified = {"past": [], "current": [], "future": []}
    for item in items:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        if any(w in text for w in future_words):
            classified["future"].append(item)
            continue
        pub = item.get("published", "")
        try:
            dt = datetime.fromisoformat(pub[:10]) if pub and len(pub) >= 10 else now
            classified["past" if dt < cutoff else "current"].append(item)
        except ValueError:
            classified["current"].append(item)
    return classified


def analyze_sentiment(items):
    pos = ["성장", "상승", "호조", "증가", "혁신", "돌파", "최고", "growth", "rise", "strong"]
    neg = ["하락", "감소", "위기", "리스크", "우려", "둔화", "decline", "crisis", "risk", "weak"]
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for item in items:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        p, n = sum(1 for w in pos if w in text), sum(1 for w in neg if w in text)
        counts["positive" if p > n else "negative" if n > p else "neutral"] += 1
    total = sum(counts.values()) or 1
    return {"counts": counts, "ratio": {k: round(v/total*100, 1) for k, v in counts.items()},
            "dominant": max(counts, key=counts.get)}


def analyze_anomalies(items):
    date_counts = defaultdict(int)
    for item in items:
        pub = item.get("published", "")[:10]
        if pub:
            date_counts[pub] += 1
    anomalies = []
    if date_counts:
        avg = sum(date_counts.values()) / len(date_counts)
        for date, count in date_counts.items():
            if count > avg * 2:
                anomalies.append({"date": date, "count": count, "average": round(avg, 1)})
    return anomalies


def run(collected_path, keyword="unknown"):
    with open(collected_path, "r", encoding="utf-8") as f:
        collected = json.load(f)
    items = []
    for r in collected:
        if r.get("status") == "success":
            items.extend(r.get("data", []))

    results = {
        "keyword": keyword, "total_items": len(items),
        "keyword_frequency": analyze_keyword_frequency(items),
        "temporal_classification": analyze_temporal(items),
        "sentiment": analyze_sentiment(items),
        "anomalies": analyze_anomalies(items),
        "analyzed_at": datetime.now().isoformat(),
    }
    output_path = str(Path(collected_path).parent / "analysis_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"분석 완료: {len(items)}건, 센티먼트={results['sentiment']['ratio']}")
    return output_path


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "reports/collected_data.json",
        sys.argv[2] if len(sys.argv) > 2 else "unknown")
'''
    with open(os.path.join(package_dir, 'analyzer.py'), 'w', encoding='utf-8') as f:
        f.write(script)


def _write_report_generator(package_dir):
    """보고서 생성 스크립트"""
    script = '''"""
보고서 생성기 — 분석 결과를 기반으로 Markdown 보고서를 생성한다.
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def generate(collected_path, analysis_path, keyword="unknown"):
    with open(collected_path, "r", encoding="utf-8") as f:
        collected = json.load(f)
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    now = datetime.now()
    sources_used = [r["source"] for r in collected if r.get("status") == "success"]
    total = analysis.get("total_items", 0)
    ratio = analysis.get("sentiment", {}).get("ratio", {})
    top_kw = analysis.get("keyword_frequency", {}).get("top_keywords", [])[:5]
    temporal = analysis.get("temporal_classification", {})

    lines = [
        f"# {keyword} 일일 트렌드 보고서\\n",
        f"> 생성일: {now.strftime('%Y-%m-%d')}  ",
        f"> 소스: {', '.join(sources_used)}  ",
        f"> 수집: {total}건 | 긍정 {ratio.get('positive',0)}% / 부정 {ratio.get('negative',0)}% / 중립 {ratio.get('neutral',0)}%\\n",
        "---\\n", "## 핵심 요약\\n",
    ]
    if top_kw:
        lines.append(f"- 상위 키워드: {', '.join(f'{w[0]}({w[1]}회)' for w in top_kw[:3])}")
    lines.append(f"- 총 {total}건 수집\\n")

    current = temporal.get("current", [])
    if current:
        lines.append("## 오늘의 주요 뉴스\\n")
        for i, item in enumerate(current[:10], 1):
            lines.append(f"{i}. **{item.get('title', 'N/A')}**")
            if item.get("link"):
                lines.append(f"   - {item['link']}")

    future = temporal.get("future", [])
    if future:
        lines.append("\\n## 전망\\n")
        for item in future[:5]:
            lines.append(f"- **{item.get('title', '')}**")

    lines.append(f"\\n---\\n_이 보고서는 투자 조언이 아닙니다._")

    report = "\\n".join(lines)
    filename = f"{keyword.replace(' ', '_')}_trend_report_{now.strftime('%Y%m%d')}.md"
    output_path = str(Path(collected_path).parent / filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"보고서 생성: {output_path}")
    return output_path, report


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "reports/collected_data.json",
             sys.argv[2] if len(sys.argv) > 2 else "reports/analysis_result.json",
             sys.argv[3] if len(sys.argv) > 3 else "unknown")
'''
    with open(os.path.join(package_dir, 'report_generator.py'), 'w', encoding='utf-8') as f:
        f.write(script)


def _write_slack_notifier(package_dir):
    """Slack 알림 스크립트 — 환경변수 우선, config.yaml 폴백 패턴 적용"""
    script = '''"""
Slack 알림 전송기
Webhook URL은 환경변수(SLACK_WEBHOOK_URL)를 우선 읽고,
없으면 config.yaml의 slack.webhook_url에서 폴백한다.
"""
import json
import os
import sys

import requests
import yaml


def send_notification(analysis_path, config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    slack_config = config.get("slack", {})

    # 필수 패턴: 환경변수 우선, config.yaml 폴백
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL") or slack_config.get("webhook_url", "")

    if not webhook_url:
        print("Slack Webhook URL 미설정 — 알림 건너뜀")
        return False

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    total = analysis.get("total_items", 0)
    ratio = analysis.get("sentiment", {}).get("ratio", {})
    top_kw = analysis.get("keyword_frequency", {}).get("top_keywords", [])[:3]
    date = analysis.get("analyzed_at", "")[:10]
    keyword = analysis.get("keyword", "")

    top_kw_str = ", ".join(f"{w[0]}({w[1]}회)" for w in top_kw) if top_kw else "데이터 부족"

    current = analysis.get("temporal_classification", {}).get("current", [])
    highlights = []
    for item in current[:3]:
        if isinstance(item, dict):
            highlights.append(f"• {item.get('title', '')[:60]}")
    highlights_str = "\\n".join(highlights) if highlights else "• 수집된 주요 뉴스 없음"

    payload = {
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": f"📊 {keyword} 일일 트렌드 보고서", "emoji": True}},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": f"*생성일:* {date}\\n*수집:* {total}건\\n"
                              f"*센티먼트:* 긍정 {ratio.get('positive',0)}% / "
                              f"부정 {ratio.get('negative',0)}% / 중립 {ratio.get('neutral',0)}%\\n"
                              f"*키워드:* {top_kw_str}"}},
            {"type": "section",
             "text": {"type": "mrkdwn", "text": f"*핵심:*\\n{highlights_str}"}},
            {"type": "context",
             "elements": [{"type": "mrkdwn", "text": "⚠️ 시장 분석이며 투자 조언이 아닙니다."}]},
        ]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"Slack 알림 전송 완료 (상태: {resp.status_code})")
        return True
    except Exception as e:
        print(f"Slack 알림 전송 실패: {e}")
        return False


if __name__ == "__main__":
    send_notification(
        sys.argv[1] if len(sys.argv) > 1 else "reports/analysis_result.json",
        sys.argv[2] if len(sys.argv) > 2 else "config.yaml")
'''
    with open(os.path.join(package_dir, 'slack_notifier.py'), 'w', encoding='utf-8') as f:
        f.write(script)


def _write_config(package_dir, keyword, domain):
    """config.yaml 작성 — webhook_url은 반드시 빈 문자열"""
    config = f"""# {keyword} 데이터 수집 파이프라인 설정

keyword: "{keyword}"
domain: "{domain or 'general'}"

keyword_expansion:
  - "{keyword}"

sources:
  rss:
    - name: "RSS Feed 1"
      url: ""  # RSS 피드 URL을 입력하세요
      enabled: false
  api:
    newsapi:
      key: ""  # https://newsapi.org 에서 발급. 또는 환경변수 NEWSAPI_KEY 사용
      enabled: false

slack:
  webhook_url: ""  # GitHub Secrets 또는 환경변수로 주입. 여기에 직접 URL을 넣지 마세요.
  enabled: true

output:
  dir: "./reports"
  keep_days: 30
"""
    with open(os.path.join(package_dir, 'config.yaml'), 'w', encoding='utf-8') as f:
        f.write(config)


def _write_github_actions(package_dir, keyword):
    """GitHub Actions workflow — templates/github_actions_template.yml 기반"""
    template_path = TEMPLATES_DIR / 'github_actions_template.yml'
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            workflow = f.read()
        # 플레이스홀더 치환
        workflow = workflow.replace('{{KEYWORD}}', keyword)
        # 엔트리포인트를 run_pipeline.py로 통일
        workflow = workflow.replace('python collect_and_report.py', 'python run_pipeline.py')
        # cron을 UTC 0시(=KST 9시)로 고정
        workflow = workflow.replace("cron: '0 9 * * *'", "cron: '0 0 * * *'")
    else:
        workflow = f"""name: Daily Data Collection - {keyword}

on:
  schedule:
    - cron: '0 0 * * *'  # UTC 0시 = KST 9시
  workflow_dispatch:

jobs:
  collect-and-analyze:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run data collection pipeline
        env:
          NEWSAPI_KEY: ${{{{ secrets.NEWSAPI_KEY }}}}
          SLACK_WEBHOOK_URL: ${{{{ secrets.SLACK_WEBHOOK_URL }}}}
        run: python run_pipeline.py

      - name: Upload report artifact
        uses: actions/upload-artifact@v4
        with:
          name: trend-report-${{{{ github.run_number }}}}
          path: reports/*.md
          retention-days: 30

      - name: Commit report to repository
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add reports/
          git diff --cached --quiet || git commit -m "chore: add daily trend report $(date +%Y-%m-%d)"
          git push
"""

    workflow_path = os.path.join(package_dir, '.github', 'workflows', 'daily_collect.yml')
    with open(workflow_path, 'w', encoding='utf-8') as f:
        f.write(workflow)


def _write_requirements(package_dir):
    with open(os.path.join(package_dir, 'requirements.txt'), 'w', encoding='utf-8') as f:
        f.write("requests>=2.31.0\nfeedparser>=6.0.10\npyyaml>=6.0.1\n")


def _write_readme(package_dir, keyword, domain):
    readme = f"""# {keyword} 데이터 수집 파이프라인

매일 자동으로 {keyword} 관련 데이터를 수집·분석하여 보고서를 생성하고 Slack으로 알림을 보냅니다.

## 파이프라인 구조

```
collector.py → collected_data.json
analyzer.py → analysis_result.json
report_generator.py → *_trend_report_YYYYMMDD.md
slack_notifier.py → Slack 알림
```

엔트리포인트: `run_pipeline.py` (위 4개를 순차 실행)

## 빠른 시작

```bash
pip install -r requirements.txt
vi config.yaml          # RSS URL 등 설정
python run_pipeline.py  # 실행
```

## GitHub Actions 자동화

1. 이 디렉토리를 GitHub에 push
2. Settings → Secrets에 추가:
   - `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL
   - `NEWSAPI_KEY`: (선택) NewsAPI 키
3. Actions 탭에서 워크플로 활성화

**매일 UTC 0시 (KST 9시)에 자동 실행됩니다.**

> ⚠️ config.yaml에 Webhook URL이나 API 키를 직접 넣지 마세요.
> GitHub Secrets → 환경변수로 주입됩니다.

## 파일 구조

```
├── run_pipeline.py              # 엔트리포인트
├── collector.py                 # 데이터 수집
├── analyzer.py                  # 분석
├── report_generator.py          # 보고서 생성
├── slack_notifier.py            # Slack 알림
├── config.yaml                  # 설정
├── requirements.txt             # 의존성
├── README.md
├── reports/                     # 출력
└── .github/workflows/
    └── daily_collect.yml        # GitHub Actions
```
"""
    with open(os.path.join(package_dir, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme)


if __name__ == '__main__':
    import sys
    keyword = sys.argv[1] if len(sys.argv) > 1 else 'AI'
    domain = sys.argv[2] if len(sys.argv) > 2 else 'tech'
    zip_path = build_automation_package(keyword, domain, output_dir='/tmp')
    print(f"패키지 생성: {zip_path}")
