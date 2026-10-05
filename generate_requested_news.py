"""Summarize locally extracted transcripts; GitHub runner never contacts YouTube."""
import csv
import importlib.util
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
REQUESTS = ROOT / "data" / "requests"
FIELDS = ["date", "title", "global_headline", "closing_summary", "featured_stocks",
          "market_movers", "issue_insight", "biotech_food_notes", "one_liner", "url"]


def load_script(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def notion(method, path, **kwargs):
    response = requests.request(method, "https://api.notion.com/v1/" + path,
        headers={"Authorization": "Bearer " + os.environ["NOTION_TOKEN"],
                 "Notion-Version": "2022-06-28"}, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def rich(value):
    value = str(value or "")
    return [{"text": {"content": value[i:i + 2000]}} for i in range(0, len(value), 2000)] or [{"text": {"content": ""}}]


def update_page(request, data):
    props = {"제목": {"title": rich(data["title"])},
             "날짜": {"date": {"start": request["date"]}},
             "처리 상태": {"select": {"name": "완료"}},
             "요약 요청": {"checkbox": False},
             "글로벌헤드라인": {"rich_text": rich(data.get("global_headline"))},
             "마감시황": {"rich_text": rich(data.get("closing_summary"))},
             "오늘장특징주": {"rich_text": rich(data.get("featured_stocks"))},
             "마켓무버": {"rich_text": rich(data.get("market_movers"))},
             "이슈인사이드": {"rich_text": rich(data.get("issue_insight"))},
             "제약바이오식품": {"rich_text": rich(data.get("biotech_food_notes"))},
             "한줄정리": {"rich_text": rich(data.get("one_liner"))},
             "영상URL": {"url": request["url"]}}
    notion("PATCH", "pages/" + request["page_id"], json={"properties": props})


def archive(data):
    path = ROOT / "data" / "archive.csv"
    rows = []
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    if data["url"] not in {row.get("url") for row in rows}:
        rows.append({key: data.get(key, "") for key in FIELDS})
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def main():
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("NOTION_TOKEN"):
        raise SystemExit("OPENAI_API_KEY and NOTION_TOKEN are required")
    summary = load_script("02_summarize_with_claude.py", "summary")
    failures = 0
    for path in sorted(REQUESTS.glob("*.json")):
        req = json.loads(path.read_text(encoding="utf-8"))
        if path.stem != req["video_id"] or not req.get("transcript") or not req.get("page_id"):
            raise ValueError(f"Invalid request: {path}")
        page = notion("GET", "pages/" + req["page_id"])
        if (page["properties"].get("처리 상태", {}).get("select") or {}).get("name") == "완료":
            continue
        try:
            data = summary.summarize_structured(req["transcript"])
            for key in ("title", "global_headline", "closing_summary", "featured_stocks",
                        "market_movers", "issue_insight", "biotech_food_notes", "one_liner"):
                if key not in data:
                    raise ValueError(f"Summary missing {key}")
            info = {key: req[key] for key in ("date", "video_id", "url", "title")}
            target = ROOT / "data" / f"summary_{req['date']}_{req['video_id']}.json"
            target.write_text(json.dumps({**data, **info}, ensure_ascii=False, indent=2), encoding="utf-8")
            post = ROOT / "_posts" / f"{req['date']}-dangjamsa-{req['video_id']}.md"
            post.write_text(summary.build_jekyll_post(data, info), encoding="utf-8")
            update_page(req, data)
            archive({**data, **info})
            print(f"Completed {req['video_id']}")
        except Exception as exc:
            failures += 1
            print(f"Failed {req['video_id']}: {exc}")
            try:
                notion("PATCH", "pages/" + req["page_id"],
                       json={"properties": {"처리 상태": {"select": {"name": "실패"}}}})
            except Exception as status_exc:
                print(f"Could not set failure status: {status_exc}")
    if failures:
        raise SystemExit(f"{failures} request(s) failed")


if __name__ == "__main__":
    main()
