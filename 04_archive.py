"""
4단계: 최신 요약 데이터를 data/archive.csv에 한 줄로 누적 저장

나중에 pandas로 읽어서 "이번 달 Fed 언급 빈도" 같은 간단한 분석을 할 수 있습니다.

사용법:
    python 04_archive.py
"""

import os
import csv
import glob
import json

ARCHIVE_PATH = os.path.join("data", "archive.csv")
FIELDS = ["date", "title", "global_headline", "closing_summary", "featured_stocks",
          "market_movers", "issue_insight", "biotech_food_notes", "one_liner", "url"]


def find_latest_summary_json() -> str:
    files = glob.glob(os.path.join("data", "summary_*.json"))
    if not files:
        raise FileNotFoundError("data/summary_*.json이 없습니다. 먼저 02번을 실행하세요.")
    # 파일명 알파벳 순이 아니라 실제로 가장 최근에 수정된 파일을 선택
    return max(files, key=os.path.getmtime)


def append_archive(data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.exists(ARCHIVE_PATH)

    # 같은 날짜가 이미 있으면 중복 추가하지 않음
    if file_exists:
        with open(ARCHIVE_PATH, "r", encoding="utf-8-sig", newline="") as f:
            existing_dates = {row["date"] for row in csv.DictReader(f)}
        if data["date"] in existing_dates:
            print(f"{data['date']}는 이미 아카이브에 있습니다. 건너뜁니다.")
            return

    with open(ARCHIVE_PATH, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: data.get(k, "") for k in FIELDS})

    print(f"아카이브 추가 완료: {ARCHIVE_PATH} ({data['date']})")


def main():
    json_path = find_latest_summary_json()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    append_archive(data)


if __name__ == "__main__":
    main()
