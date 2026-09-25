"""유튜브 영상의 한국어 자막을 transcript.txt로 저장한다.

사용법: python 01_extract_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"
URL을 생략하면 latest_video.json의 url을 사용한다.
"""

import glob
import json
import os
import re
import subprocess
import sys
import uuid

from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(video_url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([0-9A-Za-z_-]{11})", video_url)
    if not match:
        raise ValueError(f"YouTube 영상 ID를 추출할 수 없습니다: {video_url}")
    return match.group(1)


def classify_yt_dlp_error(stderr: str) -> str:
    """yt-dlp 오류 메시지를 분류한다."""
    message = stderr.lower()
    if "cookies are no longer valid" in message or ("cookie" in message and "expired" in message):
        return "COOKIE_INVALID"
    if any(s in message for s in (
        "sign in to confirm you're not a bot",
        "sign in to confirm you’re not a bot",
        "confirm you're not a bot",
        "confirm you’re not a bot",
    )):
        return "YOUTUBE_BLOCK"
    if any(s in message for s in (
        "no subtitles", "there are no subtitles", "no automatic captions",
        "requested subtitles are not available",
    )):
        return "NO_SUBTITLE"
    return "UNKNOWN"


def fetch_transcript_api(video_url: str) -> str:
    """2차 시도: 한국어 자막을 직접 요청한다."""
    print("2차 시도: youtube-transcript-api로 자막을 가져옵니다.")
    transcript = YouTubeTranscriptApi().fetch(extract_video_id(video_url), languages=["ko"])
    full_text = " ".join(snippet.text.strip() for snippet in transcript if snippet.text.strip())
    if not full_text:
        raise RuntimeError("youtube-transcript-api 응답은 성공했지만 자막 내용이 비어 있습니다.")
    print(f"✅ youtube-transcript-api 성공 ({len(full_text)}자)")
    return full_text


def _download_subtitle(video_url: str, out_dir: str, cookies_file: str | None = None) -> str:
    """실행마다 고유한 파일명을 사용해 이전 실행의 자막이 섞이지 않게 한다."""
    video_id = extract_video_id(video_url)
    os.makedirs(out_dir, exist_ok=True)
    prefix = f"{video_id}-{uuid.uuid4().hex}"
    cmd = [
        "yt-dlp", "--no-playlist", "--skip-download", "--write-sub",
        "--write-auto-sub", "--sub-lang", "ko", "--sub-format", "vtt",
        "--js-runtimes", "node", "-o", os.path.join(out_dir, f"{prefix}.%(ext)s"),
    ]
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    cmd.append(video_url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error_type = classify_yt_dlp_error(result.stderr)
        print(f"❌ yt-dlp 실패 (오류 분류: {error_type})")
        print(result.stderr)
        raise RuntimeError(f"yt-dlp 실패: {error_type}")
    vtt_files = glob.glob(os.path.join(out_dir, f"{prefix}.ko.vtt"))
    if not vtt_files:
        raise FileNotFoundError("yt-dlp는 성공했지만 한국어 VTT 자막 파일을 찾지 못했습니다.")
    return vtt_files[0]


def download_subtitle_without_cookie(video_url: str, out_dir: str = ".") -> str:
    """1차 시도: 쿠키 없이 yt-dlp 실행."""
    print("1차 시도: yt-dlp를 쿠키 없이 실행합니다.")
    path = _download_subtitle(video_url, out_dir)
    print("✅ 무쿠키 yt-dlp 성공")
    return path


def download_subtitle_with_cookie(video_url: str, out_dir: str = ".") -> str:
    """3차 시도: 환경변수에 지정된 쿠키 파일로 yt-dlp 실행."""
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if not cookies_file:
        raise RuntimeError("YOUTUBE_COOKIES_FILE 환경변수가 설정되어 있지 않습니다.")
    if not os.path.isfile(cookies_file):
        raise FileNotFoundError(f"쿠키 파일이 없습니다: {cookies_file}")
    print("3차 시도: GitHub Secret 쿠키를 사용합니다.")
    path = _download_subtitle(video_url, out_dir, cookies_file)
    print("✅ 쿠키를 사용한 yt-dlp 성공")
    return path


def vtt_to_clean_text(vtt_path: str) -> str:
    """VTT에서 시간 정보와 태그를 제거한다."""
    with open(vtt_path, "r", encoding="utf-8") as source:
        lines = source.readlines()
    text_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        if (not line or line.startswith(("WEBVTT", "Kind:", "Language:"))
                or "-->" in line or re.fullmatch(r"\d+", line)):
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            text_lines.append(clean)
    return " ".join(text_lines)


def main() -> None:
    if len(sys.argv) >= 2:
        video_url = sys.argv[1]
    else:
        if not os.path.exists("latest_video.json"):
            print("URL이 없습니다. URL을 직접 넣거나, 먼저 00_get_latest_video.py를 실행하세요.")
            sys.exit(1)
        with open("latest_video.json", "r", encoding="utf-8") as source:
            video_url = json.load(source)["url"]
        print(f"latest_video.json에서 URL을 가져왔습니다: {video_url}")

    print(f"자막 다운로드 중: {video_url}")
    text = ""
    try:
        text = vtt_to_clean_text(download_subtitle_without_cookie(video_url))
        if not text:
            raise ValueError("1차 시도에서 받은 자막 내용이 비어 있습니다.")
    except Exception as first_error:
        print(f"⚠️ 1차 실패: {first_error}")

    if not text:
        try:
            text = fetch_transcript_api(video_url)
        except Exception as second_error:
            print(f"❌ 2차 실패 ({type(second_error).__name__}): {second_error}")

    if not text:
        try:
            text = vtt_to_clean_text(download_subtitle_with_cookie(video_url))
            if not text:
                raise ValueError("3차 시도에서 받은 자막 내용이 비어 있습니다.")
        except Exception as third_error:
            raise RuntimeError("모든 자막 취득 방법이 실패했습니다.") from third_error

    with open("transcript.txt", "w", encoding="utf-8") as destination:
        destination.write(text)
    print(f"완료! transcript.txt 에 {len(text)}자 저장됨")
    print("--- 미리보기 ---")
    print(text[:300])


if __name__ == "__main__":
    main()
