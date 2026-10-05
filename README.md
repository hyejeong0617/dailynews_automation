# 당잠사 요청형 요약

보고 싶은 당잠사 영상만 Notion에서 요청합니다. Windows PC의 `MarketNews.bat`가
한국어 자막을 받아 GitHub에 전송하고, GitHub Actions는 그 자막으로 OpenAI 요약을
만들어 같은 Notion 행과 GitHub Pages에 기록합니다. 정해진 시간에 영상을 찾거나
GitHub 서버에서 YouTube에 접속하지 않습니다.

## 처음 한 번 설정

1. 저장소를 Windows PC에 `git clone`하고 Python 3.11+, Git, Node.js를 설치합니다.
2. `python -m pip install -r requirements.txt`는 첫 실행 시 자동으로 수행됩니다.
3. `.env.example`을 `.env`로 복사하고 `NOTION_TOKEN`을 입력합니다. Notion의
   `당잠사 뉴스 요약` DB에 해당 Integration을 연결합니다. `.env`는 Git에 올리지 않습니다.
4. GitHub Actions Secrets에 `OPENAI_API_KEY`와 `NOTION_TOKEN`을 등록합니다.
   기존 값이 유효하면 재등록할 필요가 없습니다. `YOUTUBE_COOKIES`와
   `YOUTUBE_API_KEY`는 이 경로에 사용하지 않습니다.
5. GitHub Pages는 기존처럼 `main` 브랜치의 루트에서 배포합니다. 로컬 Git의
   `git push` 인증과 Actions의 `contents: write` 권한이 필요합니다.

## 매번 사용

1. [당잠사 뉴스 요약 DB](https://app.notion.com/p/e8aba82c838c4a89a7680a49f54ac599)에
   새 행을 만들고 `영상URL`에 YouTube 영상 주소를 넣고 `요약 요청`을 체크합니다.
   제목은 임시로 적어도 됩니다. 영상 게시 시각을 확인할 수 없는 경우 `날짜`에
   방송의 한국 날짜를 입력합니다.
2. PC에서 `MarketNews.bat`를 더블클릭합니다. PC가 자막을 받아 저장소에
   커밋하고 푸시하면 Actions가 자동 실행됩니다.
3. Notion `처리 상태`가 `완료`가 되면 같은 행에 요약이 채워집니다.
   오류 시 `실패`와 Actions 로그를 확인합니다. 재시도는 Actions에서
   `Requested market news summaries`를 수동 실행할 수 있습니다.

한국어 자막 자체가 제공되지 않거나 집 PC에서도 YouTube 접근이 막히면 추출은
실패합니다. 브라우저 쿠키는 필요할 때 PC에서 직접 읽으며 GitHub Secret으로
전송하지 않습니다. 요청 JSON에는 영상 자막 원문이 담겨 공개 저장소에 커밋됩니다.
민감한 비공개 영상에는 사용하지 마세요.
