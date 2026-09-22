"""
3단계: data/summary_<날짜>.json 을 Notion의 '당잠사 뉴스 요약' DB에 저장

사전 준비:
    1. https://www.notion.so/my-integrations 에서 새 Integration 생성 후 토큰 복사
    2. Notion에서 '당잠사 뉴스 요약' 데이터베이스 페이지 우측 상단 '...' -> 연결 추가
       -> 방금 만든 Integration 연결 (이 단계를 빼먹으면 401 오류가 납니다)
    3. 데이터베이스 페이지의 URL에서 32자리 ID를 복사 (대시 있어도/없어도 무방)
       예: https://www.notion.so/xxx/1234abcd...?v=... 에서 1234abcd... 부분
    4. 환경변수 설정:
       set NOTION_TOKEN=여기에 Integration 토큰
       set NOTION_DATABASE_ID=여기에 데이터베이스 ID

사용법:
    python 03_save_to_notion.py
"""

import os
import sys
import glob
import json
import requests

NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def find_latest_summary_json() -> str:
    files = glob.glob(os.path.join("data", "summary_*.json"))
    if not files:
        raise FileNotFoundError("data/summary_*.json이 없습니다. 먼저 02번을 실행하세요.")
    # 파일명 알파벳 순이 아니라 실제로 가장 최근에 수정된 파일을 선택
    return max(files, key=os.path.getmtime)


def to_rich_text(text: str) -> list:
    """Notion 텍스트 속성은 조각(chunk) 하나당 2000자 제한이 있어서,
    긴 내용은 여러 조각으로 나눠 전부 저장되게 함."""
    text = text or ""
    chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)] or [""]
    return [{"text": {"content": chunk}} for chunk in chunks]


def save_to_notion(data: dict, token: str, database_id: str) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "제목": {"title": [{"text": {"content": data.get("title") or f"당잠사 뉴스 요약 - {data['date']}"}}]},
            "날짜": {"date": {"start": data["date"]}},
            "글로벌헤드라인": {"rich_text": to_rich_text(data.get("global_headline"))},
            "마감시황": {"rich_text": to_rich_text(data.get("closing_summary"))},
            "오늘장특징주": {"rich_text": to_rich_text(data.get("featured_stocks"))},
            "마켓무버": {"rich_text": to_rich_text(data.get("market_movers"))},
            "이슈인사이드": {"rich_text": to_rich_text(data.get("issue_insight"))},
            "제약바이오식품": {"rich_text": to_rich_text(data.get("biotech_food_notes"))},
            "한줄정리": {"rich_text": to_rich_text(data.get("one_liner"))},
            "영상URL": {"url": data.get("url") or None},
        },
    }
    resp = requests.post(NOTION_API_URL, headers=headers, json=payload, timeout=15)
    if resp.status_code >= 300:
        print("Notion 저장 실패:", resp.status_code, resp.text)
        resp.raise_for_status()


def main():
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        print("NOTION_TOKEN / NOTION_DATABASE_ID 환경변수가 필요합니다.")
        sys.exit(1)

    json_path = find_latest_summary_json()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    save_to_notion(data, token, database_id)
    print(f"Notion에 저장 완료: {json_path}")


if __name__ == "__main__":
    main()
