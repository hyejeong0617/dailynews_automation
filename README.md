# 당잠사 자동 요약 시스템

한국경제TV "당잠사" 재생목록의 새 영상을 매일 자동으로 찾아서 자막을 추출하고,
OpenAI로 요약한 뒤 Notion에 저장 + GitHub Pages 블로그에 게시까지 하는 파이프라인입니다.

## 폴더 구조
```
00_get_latest_video.py     0단계: 재생목록에서 새 영상 감지 (YouTube API)
01_extract_transcript.py   1단계: 자막 추출 (yt-dlp)
02_summarize_with_claude.py 2단계: 요약 (OpenAI API) -> JSON + 블로그 글 생성
03_save_to_notion.py       3단계: Notion DB에 저장
04_archive.py               4단계: CSV 아카이브에 누적
run_all.py                  위 0~4단계를 순서대로 실행하는 마스터 스크립트
_config.yml                 GitHub Pages(Jekyll) 설정
_posts/                     생성된 블로그 글 (Jekyll이 자동으로 렌더링)
data/                       구조화 데이터(JSON)와 archive.csv
.github/workflows/daily.yml GitHub Actions 자동 실행 설정
```

## A. 로컬에서 전체 파이프라인 한 번 테스트하기

### 1) 필요한 키 4개 준비
| 키 | 발급처 | 용도 |
|---|---|---|
| YOUTUBE_API_KEY | Google Cloud Console | 재생목록 최신 영상 감지 |
| OPENAI_API_KEY | platform.openai.com | 요약 생성 |
| NOTION_TOKEN | notion.so/my-integrations | Notion에 저장 |
| NOTION_DATABASE_ID | Notion DB 페이지 URL | 저장할 위치 지정 |

**YOUTUBE_API_KEY 발급 방법**
1. https://console.cloud.google.com 접속 → 새 프로젝트 생성
2. 좌측 메뉴 "API 및 서비스" → "라이브러리" → "YouTube Data API v3" 검색 후 사용 설정
3. "API 및 서비스" → "사용자 인증 정보" → "사용자 인증 정보 만들기" → "API 키"
4. 생성된 키를 복사

**NOTION_TOKEN / NOTION_DATABASE_ID 발급 방법**
1. https://www.notion.so/my-integrations 에서 "새 Integration" 생성 → 토큰(secret) 복사 → 이게 `NOTION_TOKEN`
2. Notion에서 "당잠사 뉴스 요약" 데이터베이스 페이지를 열고, 우측 상단 "..." → "연결 추가" → 방금 만든 Integration 선택
   (이 단계를 빠뜨리면 저장 시 401 오류가 납니다)
3. 데이터베이스 페이지의 브라우저 주소창 URL에서 32자리 문자열을 복사 → 이게 `NOTION_DATABASE_ID`
   예: `notion.so/내워크스페이스/1234abcd5678...?v=...` 에서 `1234abcd5678...` 부분

### 2) 명령 프롬프트에서 환경변수 설정 후 실행
```
set YOUTUBE_API_KEY=발급받은 키
set OPENAI_API_KEY=발급받은 키
set NOTION_TOKEN=발급받은 토큰
set NOTION_DATABASE_ID=발급받은 데이터베이스 ID

python run_all.py
```
성공하면 `_posts/`, `data/` 폴더가 생기고 Notion에도 새 항목이 추가됩니다.

## B. GitHub에 올려서 매일 자동 실행되게 만들기

### 1) 리포지토리 만들기
1. GitHub에서 새 리포지토리 생성 (예: `dangjamsa-automation`), Public으로 설정 (GitHub Pages 무료 사용을 위해)
2. 이 폴더의 파일 전체를 그 리포지토리에 업로드/커밋/푸시

### 2) Secrets 등록 (API 키를 코드에 직접 쓰지 않기 위함)
리포지토리 → Settings → Secrets and variables → Actions → "New repository secret"
아래 4개를 각각 등록:
- `YOUTUBE_API_KEY`
- `OPENAI_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`

### 3) GitHub Pages 활성화
리포지토리 → Settings → Pages → "Build and deployment" → Source: **Deploy from a branch**
→ Branch: `main`, 폴더: `/ (root)` 선택 → Save
몇 분 후 `https://내계정.github.io/dangjamsa-automation/` 주소로 블로그가 뜹니다.

### 4) 자동 실행 확인
`.github/workflows/daily.yml`이 평일 한국시간 오전 6시에 자동으로 실행됩니다.
리포지토리 → Actions 탭에서 실행 기록을 볼 수 있고, "Run workflow" 버튼으로 지금 바로 수동 실행도 가능합니다.
처음엔 수동 실행("workflow_dispatch")으로 한 번 테스트해보는 걸 추천합니다.

## C. 나중에 분석해보고 싶을 때
`data/archive.csv`를 엑셀이나 pandas로 열면 날짜별 요약이 쌓여있습니다.
```python
import pandas as pd
df = pd.read_csv("data/archive.csv")
df[df["fed_notes"].str.contains("금리", na=False)]  # 금리 언급된 날만 보기
```

## 막힐 수 있는 지점
- **Notion 저장 시 401 오류**: DB 페이지에 Integration을 "연결"하는 걸 빠뜨렸을 가능성이 큽니다 (위 B-2 단계 참고).
- **GitHub Actions가 자막을 못 받아옴**: yt-dlp는 가끔 유튜브 정책 변경에 영향을 받습니다. Actions 로그를 확인하고, 그래도 안되면 yt-dlp를 최신 버전으로 올려보세요 (`pip install -U yt-dlp`).
- **커밋/푸시가 실패함**: 리포지토리 Settings → Actions → General → "Workflow permissions"에서 "Read and write permissions"를 선택해야 합니다.
