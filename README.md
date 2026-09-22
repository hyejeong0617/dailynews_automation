# 당잠사 자동 요약 시스템

한국경제TV "당잠사" 재생목록의 새 영상을 매일 자동으로 찾아서 자막을 추출하고,
OpenAI로 요약한 뒤 Notion에 저장 + GitHub Pages 블로그에 게시까지 하는 파이프라인입니다.

- **블로그**: https://hyejeong0617.github.io/dailynews_automation/
- **설치/설정 방법**: [SETUP.md](./SETUP.md) 참고

## 폴더 구조
```
00_get_latest_video.py     0단계: 재생목록에서 새 영상 감지 (YouTube API)
01_extract_transcript.py   1단계: 자막 추출 (yt-dlp)
02_summarize_with_claude.py 2단계: 요약 (OpenAI API) -> JSON + 블로그 글 생성
03_save_to_notion.py       3단계: Notion DB에 저장
04_archive.py               4단계: CSV 아카이브에 누적
run_all.py                  위 0~4단계를 순서대로 실행하는 마스터 스크립트
_config.yml                 GitHub Pages(Jekyll) 설정
index.md                    GitHub Pages 홈페이지
_posts/                     생성된 블로그 글 (Jekyll이 자동으로 렌더링)
data/                       구조화 데이터(JSON)와 archive.csv
.github/workflows/daily.yml GitHub Actions 자동 실행 설정
```

## 막힐 수 있는 지점
- **Notion 저장 시 401 오류**: DB 페이지에 Integration을 "연결"하는 걸 빠뜨렸을 가능성이 큽니다.
- **GitHub Actions가 자막을 못 받아옴**: yt-dlp는 가끔 유튜브 정책 변경에 영향을 받습니다. Actions 로그를 확인하고, 그래도 안되면 yt-dlp를 최신 버전으로 올려보세요 (`pip install -U yt-dlp`).
- **커밋/푸시가 실패함**: 리포지토리 Settings → Actions → General → "Workflow permissions"에서 "Read and write permissions"를 선택해야 합니다.

자세한 키 발급, Secrets 등록, Pages 활성화 방법은 [SETUP.md](./SETUP.md)를 확인하세요.
