"""
data-collector 공통 유틸리티

이 모듈의 함수들은 모두 로컬 파일 처리 전용이며,
외부 네트워크 접근을 하지 않는다.

- YAML/JSON 파일 로드
- 도메인 감지 (키워드 매칭)
- 키워드 확장 규칙 적용
- 시즌 판단
- 출력 경로 생성
- 데이터 충분성 검사

fetch_with_retry()는 모드2 자동화 패키지에서만 사용된다.
모드1(즉시 실행)에서는 Claude의 web_search/WebFetch로 수집하므로 불필요.
"""
import time
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ── 상수 ──
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds
MIN_DATA_THRESHOLD = 3

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('data-collector')


# ============================================================
# 로컬 파일 처리 함수 (모드1, 모드2 모두 사용 가능)
# ============================================================

def load_yaml(filepath):
    """YAML 파일 로드 (로컬 파일 전용)"""
    import yaml
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(filepath):
    """JSON 파일 로드 (로컬 파일 전용)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, filepath):
    """JSON 파일 저장 (로컬 파일 전용)"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def load_config(config_path=None):
    """config.yaml 로드 및 API 키 확인 (로컬 파일 전용)"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config.yaml'

    config = load_yaml(config_path)

    available_keys = {}
    if config.get('api_keys'):
        for key_name, key_value in config['api_keys'].items():
            if key_value and key_value.strip():
                available_keys[key_name] = key_value

    config['_available_keys'] = available_keys
    return config


def load_domain_profile(domain_name):
    """도메인 프로필 YAML 로드 (로컬 파일 전용)"""
    profile_dir = Path(__file__).parent.parent / 'domain_profiles'
    profile_path = profile_dir / f'{domain_name}.yaml'

    if not profile_path.exists():
        logger.warning(f"도메인 프로필 없음: {domain_name}. general 모드로 동작.")
        return None

    return load_yaml(profile_path)


def detect_domain(keyword, profiles_dir=None):
    """키워드로 가장 적합한 도메인 감지 (로컬 파일 매칭 전용)"""
    if profiles_dir is None:
        profiles_dir = Path(__file__).parent.parent / 'domain_profiles'

    keyword_lower = keyword.lower().strip()
    best_match = None
    best_score = 0

    for profile_path in profiles_dir.glob('*.yaml'):
        profile = load_yaml(profile_path)
        domain_keywords = [k.lower() for k in profile.get('keywords', [])]

        score = 0
        for dk in domain_keywords:
            if dk in keyword_lower or keyword_lower in dk:
                score += 1
            if dk == keyword_lower:
                score += 5

        if score > best_score:
            best_score = score
            best_match = profile

    if best_match and best_score > 0:
        logger.info(f"도메인 감지: {best_match['domain']} (점수: {best_score})")
        return best_match

    logger.info(f"매칭 도메인 없음. general 모드로 동작.")
    return None


def get_season():
    """현재 월 기준 시즌 반환"""
    month = datetime.now().month
    if month in (3, 4, 5):
        return 'spring'
    elif month in (6, 7, 8):
        return 'summer'
    elif month in (9, 10, 11):
        return 'autumn'
    else:
        return 'winter'


def expand_keywords(keyword, profile):
    """키워드 확장 규칙 적용 (로컬 데이터 처리 전용)"""
    expanded = [keyword]

    if not profile or 'keyword_expansion' not in profile:
        return expanded

    rules = profile['keyword_expansion'].get('rules', [])
    current_season = get_season()

    for rule in rules:
        if rule.get('type') == 'seasonal':
            mapping = rule.get('mapping', {})
            seasonal_keywords = mapping.get(current_season, [])
            expanded.extend(seasonal_keywords)
        elif 'examples' in rule:
            examples = rule['examples']
            for trigger, expansions in examples.items():
                trigger_lower = str(trigger).lower()
                if trigger_lower in keyword.lower() or keyword.lower() in trigger_lower:
                    expanded.extend(expansions)

    seen = set()
    unique = []
    for kw in expanded:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    logger.info(f"키워드 확장: {keyword} → {unique}")
    return unique


def get_output_path(keyword, config=None):
    """보고서 출력 경로 생성"""
    date_str = datetime.now().strftime('%Y%m%d')
    safe_keyword = keyword.replace(' ', '_').replace('/', '_')
    filename = f"{safe_keyword}_trend_report_{date_str}.md"

    output_dir = '/mnt/user-data/outputs'
    if config and config.get('output_dir') and config['output_dir'].strip():
        output_dir = config['output_dir']

    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)


def format_excluded_sources(results):
    """제외된 소스 포맷팅"""
    excluded = []
    for r in results:
        if r.get('status') in ('failed', 'skipped'):
            excluded.append(f"{r.get('source', 'unknown')} (사유: {r.get('reason', 'unknown')})")
    return excluded


def check_data_sufficiency(collected_data):
    """수집 데이터 충분성 검사"""
    total = sum(
        len(r['data']) if isinstance(r.get('data'), list) else 1
        for r in collected_data
        if r.get('status') == 'success'
    )

    if total < MIN_DATA_THRESHOLD:
        logger.warning(f"수집 데이터 {total}건 < 최소 {MIN_DATA_THRESHOLD}건")
        return False, total

    return True, total


# ============================================================
# 모드2 전용: 네트워크 재시도 래퍼
# 컨테이너 내부(모드1)에서는 사용하지 않는다.
# ============================================================

def fetch_with_retry(fetch_func, source_name, *args, **kwargs):
    """
    소스별 독립 실행 + 재시도 로직

    ⚠️ 모드2(자동화 패키지) 전용.
    모드1에서는 Claude의 web_search/WebFetch 도구를 사용하므로 이 함수를 호출하지 않는다.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = fetch_func(*args, **kwargs)
            logger.info(f"[{source_name}] 수집 성공: {len(result) if isinstance(result, list) else 1}건")
            return {"status": "success", "source": source_name, "data": result}
        except Exception as e:
            if attempt < MAX_RETRIES:
                logger.warning(
                    f"[{source_name}] 시도 {attempt+1} 실패: {e}. "
                    f"{RETRY_DELAY}초 후 재시도..."
                )
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"[{source_name}] 최종 실패: {e}")
                return {
                    "status": "failed",
                    "source": source_name,
                    "reason": str(e)
                }
