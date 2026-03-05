#!/bin/bash
# 나레이션 영상 생성 - 환경 설정 스크립트
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== 나레이션 영상 생성 - 환경 설정 ==="

# --- OS 감지 ---
OS="$(uname -s)"
echo "[INFO] OS: $OS"

# --- FFmpeg 설치 확인 ---
if command -v ffmpeg &>/dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1)
    echo "[OK] FFmpeg 설치됨: $FFMPEG_VERSION"
else
    echo "[INSTALL] FFmpeg 설치 중..."
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install ffmpeg
        else
            echo "[ERROR] Homebrew가 필요합니다. https://brew.sh 에서 설치하세요."
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y ffmpeg
        elif command -v yum &>/dev/null; then
            sudo yum install -y ffmpeg
        else
            echo "[ERROR] 패키지 매니저를 찾을 수 없습니다. FFmpeg를 수동 설치하세요."
            exit 1
        fi
    else
        echo "[ERROR] 지원하지 않는 OS입니다. FFmpeg를 수동 설치하세요."
        exit 1
    fi
    echo "[OK] FFmpeg 설치 완료"
fi

# --- ffprobe 확인 ---
if command -v ffprobe &>/dev/null; then
    echo "[OK] ffprobe 사용 가능"
else
    echo "[WARN] ffprobe를 찾을 수 없습니다. FFmpeg 재설치를 권장합니다."
fi

# --- Python 의존성 설치 ---
echo "[INSTALL] Python 의존성 설치 중..."
pip3 install --quiet --upgrade google-genai pyyaml python-dotenv 2>/dev/null || \
pip install --quiet --upgrade google-genai pyyaml python-dotenv 2>/dev/null || \
{
    echo "[ERROR] pip 설치 실패. Python 3.9+ 및 pip가 설치되어 있는지 확인하세요."
    exit 1
}
echo "[OK] Python 의존성 설치 완료 (google-genai, pyyaml, python-dotenv)"

# --- 한글 폰트 확인 ---
FONT_FOUND=false

if [ "$OS" = "Darwin" ]; then
    # macOS: 시스템 한글 폰트 확인
    if fc-list 2>/dev/null | grep -qi "noto.*cjk\|apple.*gothic\|malgun\|nanumgothic"; then
        FONT_FOUND=true
        echo "[OK] 한글 폰트 발견 (macOS)"
    elif [ -f "/System/Library/Fonts/AppleSDGothicNeo.ttc" ]; then
        FONT_FOUND=true
        echo "[OK] Apple SD Gothic Neo 폰트 발견"
    fi
elif [ "$OS" = "Linux" ]; then
    if fc-list 2>/dev/null | grep -qi "noto.*cjk\|nanumgothic"; then
        FONT_FOUND=true
        echo "[OK] 한글 폰트 발견 (Linux)"
    fi
fi

if [ "$FONT_FOUND" = false ]; then
    echo "[INSTALL] 한글 폰트 설치 중..."
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install --cask font-noto-sans-cjk-kr 2>/dev/null || \
            echo "[WARN] 폰트 자동 설치 실패. macOS 기본 한글 폰트를 사용합니다."
        fi
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y fonts-noto-cjk 2>/dev/null || true
        fi
    fi
fi

# --- 디렉토리 생성 ---
mkdir -p "$PROJECT_DIR/output/segments"
mkdir -p "$PROJECT_DIR/output/logs"
echo "[OK] 출력 디렉토리 생성 완료"

# --- .env 파일 확인 ---
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "[OK] .env 파일 존재"
elif [ -f "$PROJECT_DIR/.env.example" ]; then
    echo "[WARN] .env 파일이 없습니다. .env.example을 복사하세요:"
    echo "       cp .env.example .env"
    echo "       GEMINI_API_KEY를 설정하세요."
else
    echo "[WARN] GEMINI_API_KEY 환경변수가 설정되어 있는지 확인하세요."
fi

# --- 최종 확인 ---
echo ""
echo "=== 환경 설정 완료 ==="
echo "필수 확인사항:"
echo "  1. GEMINI_API_KEY가 설정되어 있는지 확인"
echo "  2. FFmpeg: $(command -v ffmpeg || echo 'NOT FOUND')"
echo "  3. Python: $(python3 --version 2>/dev/null || echo 'NOT FOUND')"
echo ""
