#!/usr/bin/env bash
set -euo pipefail

# generate-shorts 환경 설정 스크립트
# claude.ai 컨테이너(Ubuntu 24) + 로컬 macOS 모두 지원

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== generate-shorts 환경 설정 ==="

# 컨테이너 환경 감지
IS_CONTAINER=0
if [[ -d "/home/claude" ]] || [[ "${CLAUDE_CONTAINER:-}" == "1" ]] || [[ -f "/.dockerenv" ]]; then
    IS_CONTAINER=1
    echo -e "${YELLOW}[INFO]${NC} 컨테이너 환경 감지됨"
fi

# --- 1. ffmpeg ---
if command -v ffmpeg &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
else
    echo -e "${YELLOW}[INSTALL]${NC} ffmpeg 설치 중..."
    if [[ "$(uname)" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install ffmpeg
        else
            echo -e "${RED}[ERROR]${NC} Homebrew가 필요합니다: https://brew.sh"
            exit 1
        fi
    else
        # Linux: sudo 없이 먼저 시도, 실패하면 sudo로 재시도
        apt-get update && apt-get install -y ffmpeg 2>/dev/null || \
        sudo apt-get update && sudo apt-get install -y ffmpeg 2>/dev/null || {
            echo -e "${RED}[ERROR]${NC} ffmpeg 설치 실패 - 수동 설치 필요"
            exit 1
        }
    fi
    echo -e "${GREEN}[OK]${NC} ffmpeg 설치 완료"
fi

# --- 2. yt-dlp ---
if command -v yt-dlp &>/dev/null; then
    echo -e "${GREEN}[OK]${NC} yt-dlp: $(yt-dlp --version)"
    echo -e "${YELLOW}[UPDATE]${NC} yt-dlp 최신 버전 확인..."
    yt-dlp -U 2>/dev/null || \
    pip3 install --upgrade yt-dlp --break-system-packages 2>/dev/null || \
    pip3 install --user --upgrade yt-dlp 2>/dev/null || true
else
    echo -e "${YELLOW}[INSTALL]${NC} yt-dlp 설치 중..."
    pip3 install yt-dlp --break-system-packages 2>/dev/null || \
    pip install yt-dlp --break-system-packages 2>/dev/null || \
    pip3 install --user yt-dlp 2>/dev/null || {
        if command -v brew &>/dev/null; then
            brew install yt-dlp
        else
            echo -e "${RED}[ERROR]${NC} yt-dlp 설치 실패"
            exit 1
        fi
    }
    echo -e "${GREEN}[OK]${NC} yt-dlp 설치 완료"
fi

# --- 3. 한글 폰트 (Linux) ---
if [[ "$(uname)" != "Darwin" ]]; then
    FONT_FOUND=0
    for font_path in \
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc" \
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf" \
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"; do
        if [[ -f "$font_path" ]]; then
            FONT_FOUND=1
            echo -e "${GREEN}[OK]${NC} 한글 폰트: $font_path"
            break
        fi
    done

    if [[ "$FONT_FOUND" -eq 0 ]]; then
        echo -e "${YELLOW}[INSTALL]${NC} 한글 폰트(Noto Sans CJK) 설치 중..."
        apt-get install -y fonts-noto-cjk 2>/dev/null || \
        sudo apt-get install -y fonts-noto-cjk 2>/dev/null || {
            echo -e "${YELLOW}[WARN]${NC} 한글 폰트 설치 실패 - 인트로/자막 한글이 깨질 수 있습니다"
            echo "  수동 설치: apt-get install fonts-noto-cjk"
        }
        # 폰트 캐시 갱신
        fc-cache -f 2>/dev/null || true
    fi
else
    echo -e "${GREEN}[OK]${NC} 한글 폰트: macOS 내장"
fi

# --- 4. 환경 설정 안내 ---
echo ""
echo "=== 봇 감지 우회 설정 ==="
if [[ "$IS_CONTAINER" -eq 1 ]]; then
    echo -e "${YELLOW}[INFO]${NC} 컨테이너 환경 - 브라우저 쿠키 사용 불가"
    echo "  쿠키 필요 시: cookies.txt 파일을 작업 디렉토리에 배치"
else
    COOKIE_BROWSER="${YT_COOKIE_BROWSER:-chrome}"
    echo -e "${GREEN}[OK]${NC} 쿠키 브라우저: ${COOKIE_BROWSER}"
    echo "  (변경: export YT_COOKIE_BROWSER=firefox|safari|edge)"
fi

if [[ -n "${YT_PROXY:-}" ]]; then
    echo -e "${GREEN}[OK]${NC} 프록시: ${YT_PROXY}"
else
    echo -e "${YELLOW}[INFO]${NC} 프록시 미설정 (선택: export YT_PROXY=socks5://...)"
fi

# --- 5. 작업 디렉토리 ---
mkdir -p output/shorts output/logs
echo -e "${GREEN}[OK]${NC} 작업 디렉토리: output/, output/shorts/, output/logs/"

echo ""
echo "=== 환경 설정 완료 ==="
echo "실행: python3 scripts/run_pipeline.py --url [유튜브URL] --count 10 --lang ko"
