"""
2단계: transcript.txt를 OpenAI API에 보내 구조화된 요약(JSON)과
       블로그 포스트(Jekyll 글) 두 가지 형태로 저장

사전 준비:
    - OpenAI API 키가 필요합니다: https://platform.openai.com
    - 환경변수로 설정: set OPENAI_API_KEY=여기에 키 입력

입력:
    - transcript.txt (1단계 결과물)
    - latest_video.json (0단계 결과물, 있으면 영상 게시일/제목/URL을 사용)

출력:
    - data/summary_<날짜>.json   (Notion 저장, 아카이브용 구조화 데이터)
    - _posts/<날짜>-dangjamsa.md (GitHub Pages/Jekyll 블로그 글)
"""

import os
import json
import datetime

from openai import OpenAI

PROMPT_TEMPLATE = """\
다음은 한국경제TV "당잠사(당신이 잠든 사이에)" 채널의 스크립트야.
이 영상은 보통 [글로벌 헤드라인 - 마감 시황 - 오늘장 특징주 - 마켓무버 - 이슈 인사이드]
순서의 코너로 구성돼. 스크립트에서 각 코너에 해당하는 내용을 찾아 구분해서,
아래 JSON 형식으로만 응답해줘. 다른 설명 문장은 붙이지 마.

**중요 1**: 스크립트에 언급된 종목, 기업, 인물, 국가, 이벤트는 절대 임의로 몇 개만
골라서 요약하지 말고 전부 빠짐없이 담아줘. 예를 들어 "특징주 2~3개만" 같은 식으로
개수를 스스로 제한하지 마. 제약회사, 지정학 이슈(유엔총회, 미중회담 등), 원자재,
채권 등 스크립트에 나온 모든 소재를 포함해. 각 항목은 숫자(등락률, 가격, 금액)와
배경/원인까지 포함해서 상세하게 적어줘. 사실은 스크립트 내용에만 근거하고,
자동자막 특성상 숫자/고유명사가 어색하면 맥락상 자연스럽게 보정해줘.
해당 코너 내용이 스크립트에 없으면 "언급 없음"이라고 적어줘.

**중요 2**: 별도로 "biotech_food_notes" 항목을 만들어서, 제약/바이오/헬스케어/식품
관련 언급을 전부 모아줘. 이 카테고리는 다른 코너(특징주, 마켓무버 등)에서 비중이
작게 다뤄지거나 스쳐 지나가듯 언급되더라도, 여기서는 절대 누락하지 말고 별도로
꺼내서 상세히 적어줘. 예: 특정 제약회사의 임상 결과, 신약 승인, 인수합병, FDA 관련
소식, 식품기업 실적/이슈 등. 해당 내용이 스크립트에 전혀 없으면 "언급 없음"이라고 적어줘.

{{
  "title": "한 줄 제목 (예: 비트코인 급등과 메타 AI 훈풍)",
  "global_headline": "글로벌 헤드라인: 오늘 스크립트 맨 앞에 나온 전체 글로벌 이슈를 모두 나열하며 설명 (배경/맥락 포함, 길이 제한 없음)",
  "closing_summary": "마감 시황: 다우/나스닥/S&P500 등락률, 국제유가·환율·국채금리 등 마감 지표 전체와 그 원인",
  "featured_stocks": "오늘장 특징주: 스크립트에 나온 특징주 전부를 각각 줄바꿈으로 구분해서, 종목명-등락률-이유 순으로. 개수를 임의로 줄이지 말 것",
  "market_movers": "마켓무버: 시장을 움직인 이슈/인물/이벤트를 전부 각각 줄바꿈으로 구분해서 배경과 파급효과까지",
  "issue_insight": "이슈 인사이드: 심층 분석 코너에서 다룬 모든 소재(지정학, 정책, 기업 이슈 등)를 문단으로 정리 (전망, 전문가 의견 포함)",
  "biotech_food_notes": "제약/바이오/식품 소식: 위 코너들에서 비중이 작았더라도 관련 언급을 전부 모아 상세히 정리 (회사명, 내용, 숫자 포함)",
  "one_liner": "오늘 기억할 핵심 포인트 한 문장"
}}

--- 스크립트 원문 ---
{transcript}
"""


def summarize_structured(transcript: str) -> dict:
    client = OpenAI()
    prompt = PROMPT_TEMPLATE.format(transcript=transcript)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=4500,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.choices[0].message.content)


def load_video_info() -> dict:
    """0단계 결과가 있으면 그걸 쓰고, 없으면(수동 테스트) 오늘 날짜로 대체."""
    if os.path.exists("latest_video.json"):
        with open("latest_video.json", "r", encoding="utf-8") as f:
            info = json.load(f)
        # published_at 예: "2026-09-22T05:30:00Z" -> 날짜만 추출
        info["date"] = info["published_at"][:10]
        return info

    today = datetime.date.today().isoformat()
    return {"video_id": None, "title": "", "url": "", "date": today}


def build_jekyll_post(data: dict, video_info: dict) -> str:
    front_matter = (
        "---\n"
        "layout: post\n"
        f"title: \"{data['title']}\"\n"
        f"date: {video_info['date']}\n"
        "categories: [당잠사]\n"
        "---\n\n"
    )
    body = (
        f"## 오늘의 미국 시장 브리핑 ({video_info['date']})\n\n"
        f"### 1. 글로벌 헤드라인\n{data['global_headline']}\n\n"
        f"### 2. 마감 시황\n{data['closing_summary']}\n\n"
        f"### 3. 오늘장 특징주\n{data['featured_stocks']}\n\n"
        f"### 4. 마켓무버\n{data['market_movers']}\n\n"
        f"### 5. 이슈 인사이드\n{data['issue_insight']}\n\n"
        f"### 6. 제약·바이오·식품 소식\n{data['biotech_food_notes']}\n\n"
        f"### 오늘의 한 줄 정리\n{data['one_liner']}\n\n"
        f"> 원본 영상: [{video_info.get('title', '')}]({video_info.get('url', '')})\n"
    )
    return front_matter + body


def main():
    if not os.path.exists("transcript.txt"):
        print("transcript.txt가 없습니다. 먼저 01_extract_transcript.py를 실행하세요.")
        return None

    with open("transcript.txt", "r", encoding="utf-8") as f:
        transcript = f.read()

    print("OpenAI API로 요약 요청 중...")
    data = summarize_structured(transcript)
    video_info = load_video_info()
    date = video_info["date"]

    # 1) 구조화 데이터 저장 (Notion, 아카이브에서 재사용)
    os.makedirs("data", exist_ok=True)
    data_out = {**data, **video_info}
    json_path = os.path.join("data", f"summary_{date}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)

    # 2) Jekyll 블로그 글 저장
    os.makedirs("_posts", exist_ok=True)
    post_path = os.path.join("_posts", f"{date}-dangjamsa.md")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(build_jekyll_post(data, video_info))

    print(f"완료!\n- 구조화 데이터: {json_path}\n- 블로그 글: {post_path}")
    return data_out


if __name__ == "__main__":
    main()
