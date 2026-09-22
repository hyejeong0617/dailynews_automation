"""
전체 파이프라인 실행: 새 영상 감지 -> 자막 추출 -> 요약 -> Notion 저장 -> 아카이브

GitHub Actions에서 매일 이 스크립트 하나만 실행하면 됩니다.
로컬에서 수동으로 전체 흐름을 테스트할 때도 이 스크립트를 쓰면 됩니다.

사용법:
    python run_all.py
"""

import os
import re
import sys
import json
import subprocess

import importlib.util


def extract_video_id(url_or_id: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([0-9A-Za-z_-]{11})", url_or_id)
    return match.group(1) if match else url_or_id


def run(script: str, *args: str) -> None:
    """하위 스크립트를 별도 프로세스로 실행하고, 실패하면 즉시 중단."""
    cmd = [sys.executable, script, *args]
    print(f"\n=== 실행: {' '.join(cmd)} ===")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"{script} 실행 중 오류가 발생해 파이프라인을 중단합니다.")
        sys.exit(result.returncode)


def import_module(path: str, name: str):
    """파일명이 숫자로 시작해 일반 import가 안 되는 스크립트를 불러오는 헬퍼."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    step0 = import_module("00_get_latest_video.py", "step0")

    # 테스트 모드: OVERRIDE_VIDEO_URL 환경변수나 커맨드라인 인자로 특정 영상을 강제 지정
    override_url = os.environ.get("OVERRIDE_VIDEO_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)

    if override_url:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        video_id = extract_video_id(override_url)
        video = step0.fetch_video_by_id(api_key, video_id)
        with open("latest_video.json", "w", encoding="utf-8") as f:
            json.dump(video, f, ensure_ascii=False, indent=2)
        print(f"[테스트 모드] 지정한 영상으로 강제 실행: {video['title']}")
        skip_last_id_update = True
    else:
        has_new_video = step0.main()
        if not has_new_video:
            print("처리할 새 영상이 없습니다. 파이프라인을 종료합니다.")
            return
        with open("latest_video.json", "r", encoding="utf-8") as f:
            video = json.load(f)
        skip_last_id_update = False

    # 1단계: 자막 추출
    run("01_extract_transcript.py", video["url"])

    # 2단계: 요약 (JSON + 블로그 글 생성)
    run("02_summarize_with_claude.py")

    # 3단계: Notion 저장
    run("03_save_to_notion.py")

    # 4단계: 아카이브
    run("04_archive.py")

    # 테스트 모드가 아닐 때만, 전부 성공했을 때 "처리 완료"로 기록
    # (테스트 모드에서 기록해버리면 나중에 실제 최신 영상이 이 영상이라서 건너뛰게 될 수 있음)
    if not skip_last_id_update:
        step0.save_last_video_id(video["video_id"])
    print(f"\n파이프라인 완료: {video['title']}")


if __name__ == "__main__":
    main()
