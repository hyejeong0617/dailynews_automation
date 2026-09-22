"""
0단계: 재생목록에서 아직 처리하지 않은 최신 영상을 자동으로 찾기

사전 준비:
    - YouTube Data API v3 키가 필요합니다 (Google Cloud Console에서 발급)
    - 환경변수로 설정: set YOUTUBE_API_KEY=여기에 키 입력

동작 방식:
    - last_video_id.txt 에 마지막으로 처리한 영상 ID를 기억해둡니다.
    - 재생목록에서 가장 최근에 올라온 영상을 찾아, 그게 이미 처리한 영상이면
      "새 영상 없음"으로 종료합니다.
    - 새 영상이면 latest_video.json에 정보(영상ID, 제목, URL, 게시일)를 저장합니다.
"""

import os
import json
import requests

PLAYLIST_ID = "PLh6kUo7pqm_69KUuM0hOj-ClLo6GWdgUH"  # 당잠사 재생목록
LAST_VIDEO_FILE = "last_video_id.txt"
OUTPUT_FILE = "latest_video.json"


def fetch_recent_items(api_key: str, playlist_id: str, max_results: int = 10) -> list:
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "contentDetails,snippet",
        "playlistId": playlist_id,
        "maxResults": max_results,
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


def pick_latest(items: list) -> dict:
    """게시일(videoPublishedAt) 기준으로 가장 최근 영상 선택."""
    latest = max(items, key=lambda i: i["contentDetails"]["videoPublishedAt"])
    video_id = latest["contentDetails"]["videoId"]
    return {
        "video_id": video_id,
        "title": latest["snippet"]["title"],
        "published_at": latest["contentDetails"]["videoPublishedAt"],  # 예: 2026-09-22T05:30:00Z
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def fetch_video_by_id(api_key: str, video_id: str) -> dict:
    """특정 영상 ID의 정보를 직접 조회 (테스트 시 특정 영상을 지정할 때 사용)."""
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet", "id": video_id, "key": api_key}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise ValueError(f"영상을 찾을 수 없습니다: {video_id}")
    snippet = items[0]["snippet"]
    return {
        "video_id": video_id,
        "title": snippet["title"],
        "published_at": snippet["publishedAt"],
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def load_last_video_id() -> str | None:
    if os.path.exists(LAST_VIDEO_FILE):
        with open(LAST_VIDEO_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    return None


def save_last_video_id(video_id: str) -> None:
    with open(LAST_VIDEO_FILE, "w", encoding="utf-8") as f:
        f.write(video_id)


def main() -> bool:
    """새 영상이 있으면 True와 latest_video.json 생성, 없으면 False."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.")

    items = fetch_recent_items(api_key, PLAYLIST_ID)
    if not items:
        print("재생목록에서 영상을 가져오지 못했습니다.")
        return False

    latest = pick_latest(items)
    last_id = load_last_video_id()

    if latest["video_id"] == last_id:
        print(f"새 영상 없음 (마지막 처리: {latest['title']})")
        return False

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)

    print(f"새 영상 발견: {latest['title']}")
    print(f"URL: {latest['url']}")
    return True


if __name__ == "__main__":
    found = main()
    if found:
        # last_video_id.txt 갱신은 전체 파이프라인이 끝까지 성공한 뒤
        # run_all.py에서 처리합니다 (중간에 실패하면 다음날 재시도되도록).
        pass
