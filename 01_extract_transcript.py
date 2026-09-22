"""
1단계: 유튜브 영상의 한국어 자막을 텍스트로 추출

사용법:
    python 01_extract_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

결과: 같은 폴더에 transcript.txt 파일 생성 (타임스탬프 제거된 순수 텍스트)
"""

import sys
import re
import json
import subprocess
import glob
import os


def download_subtitle(video_url: str, out_dir: str = ".") -> str:
    """yt-dlp로 한국어 자막(자동/수동)만 다운로드. 영상 자체는 받지 않음."""
    cmd = [
        "yt-dlp",
        "--no-playlist",         # URL에 재생목록 정보가 섞여 있어도 해당 영상 1개만 처리
        "--skip-download",       # 영상은 받지 않고 자막만
        "--write-sub",           # 수동 자막이 있으면 우선 사용
        "--write-auto-sub",      # 없으면 자동생성 자막 사용
        "--sub-lang", "ko",
        "--sub-format", "vtt",
        "-o", os.path.join(out_dir, "%(id)s.%(ext)s"),
        video_url,
    ]
    subprocess.run(cmd, check=True)

    # 다운로드된 .vtt 파일 찾기
    vtt_files = glob.glob(os.path.join(out_dir, "*.ko.vtt"))
    if not vtt_files:
        raise FileNotFoundError(
            "한국어 자막을 찾지 못했습니다. 이 영상에 자막이 없을 수 있습니다."
        )
    return vtt_files[0]


def vtt_to_clean_text(vtt_path: str) -> str:
    """VTT 자막 파일에서 타임스탬프/메타데이터를 제거하고 순수 대화 텍스트만 추출."""
    with open(vtt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text_lines = []
    seen = set()  # 자동자막 특성상 같은 줄이 중복되는 경우가 많아서 제거
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:  # 타임스탬프 줄
            continue
        if re.match(r"^\d+$", line):  # 순번만 있는 줄
            continue
        # <c> 같은 스타일 태그 제거
        clean = re.sub(r"<[^>]+>", "", line)
        if clean and clean not in seen:
            seen.add(clean)
            text_lines.append(clean)

    return " ".join(text_lines)


def main():
    if len(sys.argv) >= 2:
        video_url = sys.argv[1]
    else:
        # 0단계(00_get_latest_video.py)가 만들어둔 latest_video.json에서 자동으로 URL 가져오기
        if not os.path.exists("latest_video.json"):
            print("URL이 없습니다. URL을 직접 넣거나, 먼저 00_get_latest_video.py를 실행하세요.")
            sys.exit(1)
        with open("latest_video.json", "r", encoding="utf-8") as f:
            video_url = json.load(f)["url"]
        print(f"latest_video.json에서 URL을 가져왔습니다: {video_url}")

    print(f"자막 다운로드 중: {video_url}")

    vtt_path = download_subtitle(video_url)
    print(f"자막 파일: {vtt_path}")

    text = vtt_to_clean_text(vtt_path)

    with open("transcript.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"완료! transcript.txt 에 {len(text)}자 저장됨")
    print("--- 미리보기 ---")
    print(text[:300])


if __name__ == "__main__":
    main()
