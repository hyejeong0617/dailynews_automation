"""
전체 파이프라인 실행: 새 영상 감지 -> 자막 추출 -> 요약 -> Notion 저장 -> 아카이브

GitHub Actions에서 매일 이 스크립트 하나만 실행하면 됩니다.
로컬에서 수동으로 전체 흐름을 테스트할 때도 이 스크립트를 쓰면 됩니다.

사용법:
    python run_all.py
"""

import sys
import json
import subprocess

import importlib.util


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
    # 0단계: 새 영상 있는지 확인
    step0 = import_module("00_get_latest_video.py", "step0")
    has_new_video = step0.main()
    if not has_new_video:
        print("처리할 새 영상이 없습니다. 파이프라인을 종료합니다.")
        return

    with open("latest_video.json", "r", encoding="utf-8") as f:
        video = json.load(f)

    # 1단계: 자막 추출
    run("01_extract_transcript.py", video["url"])

    # 2단계: 요약 (JSON + 블로그 글 생성)
    run("02_summarize_with_claude.py")

    # 3단계: Notion 저장
    run("03_save_to_notion.py")

    # 4단계: 아카이브
    run("04_archive.py")

    # 여기까지 전부 성공했을 때만 "처리 완료"로 기록 (중간 실패 시 다음날 재시도됨)
    step0.save_last_video_id(video["video_id"])
    print(f"\n파이프라인 완료: {video['title']}")


if __name__ == "__main__":
    main()
