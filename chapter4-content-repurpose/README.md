# Content Repurpose Skill

원소스 멀티콘텐츠 자동 생성 스킬 - 하나의 원본 콘텐츠를 여러 플랫폼에 최적화된 콘텐츠로 변환합니다.

## 설치 방법

### 방법 1: 프로젝트에 직접 복사

1. 프로젝트 루트에 `.claude/commands/` 디렉토리가 없으면 생성합니다:
```bash
mkdir -p .claude/commands
```

2. 파일을 복사합니다:
```bash
# 슬래시 명령어 파일
cp .claude/commands/repurpose.md [프로젝트]/.claude/commands/repurpose.md

# 스킬 정의 파일 (선택 - 상세 플랫폼 규칙 참조용)
cp repurpose.md [프로젝트]/repurpose.md
```

### 방법 2: zip 파일에서 설치

1. zip 파일을 압축 해제합니다.
2. `.claude/commands/repurpose.md` 파일을 프로젝트의 `.claude/commands/` 디렉토리에 복사합니다.
3. (선택) `repurpose.md`를 프로젝트 루트에 복사하면 상세 플랫폼 규칙을 참조할 수 있습니다.

## 사용법

Claude Code에서 다음 명령어를 사용합니다:

### 콘텐츠 변환 (기본)
```
/repurpose
```
대화형으로 원본 콘텐츠 입력, 플랫폼 선택, 콘텐츠 생성을 진행합니다.

```
/repurpose [원본 텍스트를 여기에 붙여넣기]
```
입력된 텍스트를 원본으로 바로 변환을 시작합니다.

### 콘텐츠 감사
```
/repurpose audit
```
기존 콘텐츠 라이브러리를 분석하여 부족한 주제, 중복, 개선 포인트를 도출합니다.

### 갭 분석
```
/repurpose gap
```
경쟁 채널/사이트 대비 콘텐츠 갭을 분석합니다.

## 지원 플랫폼

사용자가 실행 시 원하는 플랫폼을 선택할 수 있습니다:

| 플랫폼 | 특성 |
|--------|------|
| SEO 블로그 포스트 | 키워드 최적화, H2/H3 구조 |
| X (Twitter) 스레드 | 140자 분할, 훅-인사이트-CTA |
| LinkedIn 게시물 | 전문가 톤, 경험 공유형 |
| Instagram 캡션 | 감성적, 해시태그 30개 |
| 뉴스레터 본문 | 1:1 대화형, 오픈율 최적화 |
| 썸네일/비주얼 가이드 | 텍스트, 색상, 레이아웃 |
| YouTube Shorts 스크립트 | 30~60초, 3초 훅 |
| TikTok 스크립트 | 숏폼, 에너지 넘치는 톤 |
| Facebook 게시물 | 커뮤니티형, 공유 유도 |
| Pinterest 핀 설명 | 검색 최적화, 실용적 |
| Threads 게시물 | 캐주얼, 트렌디 |
| 브런치 글 | 에세이형, 깊이 있는 서술 |

## 파일 구조

```
content-repurpose/
├── .claude/
│   └── commands/
│       └── repurpose.md      # /repurpose 슬래시 명령어 (핵심 파일)
├── repurpose.md              # 스킬 정의 (상세 플랫폼 규칙)
└── README.md                 # 이 파일
```

## 출력 언어

모든 콘텐츠는 한국어로 생성됩니다.
