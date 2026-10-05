"""Collect only checked Notion news requests on a local PC and push transcripts."""
import json
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
REQUESTS = ROOT / "data" / "requests"
NOTION_VERSION = "2022-06-28"


def video_id(url):
    match = re.search(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{11})(?:\b|$)", url)
    if not match:
        raise ValueError(f"Invalid YouTube URL: {url}")
    return match.group(1)


def notion(method, path, **kwargs):
    response = requests.request(method, "https://api.notion.com/v1/" + path,
        headers={"Authorization": "Bearer " + os.environ["NOTION_TOKEN"],
                 "Notion-Version": NOTION_VERSION}, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def queue():
    pages, cursor = [], None
    while True:
        body = {"filter": {"and": [
            {"property": "요약 요청", "checkbox": {"equals": True}},
            {"property": "처리 상태", "select": {"does_not_equal": "완료"}}]},
            "page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        result = notion("POST", "databases/" + os.environ["NOTION_DATABASE_ID"] + "/query", json=body)
        pages += result["results"]
        cursor = result.get("next_cursor")
        if not cursor:
            return pages


def status(page_id, name):
    notion("PATCH", "pages/" + page_id,
           json={"properties": {"처리 상태": {"select": {"name": name}}}})


def extract(url, vid, browser):
    """Download Korean subtitles locally; browser cookies stay on the PC."""
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("extractor", ROOT / "01_extract_transcript.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    errors = []
    for use_browser in (False, True):
        if use_browser and not browser:
            continue
        command = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--skip-download", "--print-json",
                   "--write-sub", "--write-auto-sub", "--sub-langs", "ko,ko-KR",
                   "--sub-format", "vtt", "--js-runtimes", "node",
                   "--remote-components", "ejs:github", "-o", str(REQUESTS / (vid + ".%(ext)s"))]
        if use_browser:
            command += ["--cookies-from-browser", browser]
        result = subprocess.run(command + [url], capture_output=True, text=True, encoding="utf-8", errors="replace")
        candidates = list(REQUESTS.glob(vid + "*.vtt"))
        if result.returncode == 0 and candidates:
            text = module.vtt_to_clean_text(str(candidates[0]))
            for file in candidates:
                file.unlink()
            if len(text.strip()) >= 50:
                try:
                    info = json.loads(result.stdout.strip().splitlines()[-1])
                except (ValueError, IndexError):
                    info = {}
                return text, info
        for file in candidates:
            file.unlink()
        errors.append(result.stderr[-900:])
    raise RuntimeError("Local subtitle extraction failed:\n" + "\n".join(errors))


def main():
    load_dotenv(ROOT / ".env")
    if not os.getenv("NOTION_TOKEN"):
        raise SystemExit("Set NOTION_TOKEN in .env")
    os.environ.setdefault("NOTION_DATABASE_ID", "e8aba82c838c4a89a7680a49f54ac599")
    REQUESTS.mkdir(parents=True, exist_ok=True)
    saved, failures = [], 0
    for page in queue():
        page_id = page["id"]
        url = (page["properties"].get("영상URL") or {}).get("url")
        try:
            if not url:
                raise ValueError("영상URL is empty")
            vid = video_id(url)
            path = REQUESTS / (vid + ".json")
            if not path.exists():
                text, info = extract(url, vid, os.getenv("YOUTUBE_BROWSER", "chrome"))
                requested_date = (page["properties"].get("날짜") or {}).get("date") or {}
                timestamp = info.get("release_timestamp") or info.get("timestamp")
                broadcast_date = (datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
                    .astimezone(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
                    if timestamp else requested_date.get("start"))
                if not broadcast_date:
                    raise ValueError("Could not determine broadcast date; set 날짜 in Notion and retry")
                path.write_text(json.dumps({"page_id": page_id, "video_id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}", "transcript": text,
                    "date": broadcast_date, "title": info.get("title", "")},
                    ensure_ascii=False, indent=2), encoding="utf-8")
            saved.append(path)
            status(page_id, "자막 준비")
        except Exception as exc:
            failures += 1
            print(f"Failed {page_id}: {exc}", file=sys.stderr)
            status(page_id, "실패")
    if saved:
        paths = [str(p.relative_to(ROOT)) for p in saved]
        subprocess.run(["git", "add", "--", *paths], cwd=ROOT, check=True)
        changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode
        if changed:
            subprocess.run(["git", "commit", "-m", "Add requested market news transcripts"], cwd=ROOT, check=True)
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
    print(f"Ready: {len(saved)}, failed: {failures}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
