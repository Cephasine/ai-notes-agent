import json
import shutil

import config
from gemini_analyzer import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, analyze_file
from notion_writer import create_note

SUPPORTED_EXT = VIDEO_EXT | IMAGE_EXT | AUDIO_EXT


def load_log() -> dict:
    if config.LOG_FILE.exists():
        return json.loads(config.LOG_FILE.read_text())
    return {}


def save_log(log: dict):
    config.LOG_FILE.write_text(json.dumps(log, indent=2))


def print_report(analysis: dict, filename: str):
    print(f"\n=== {filename} ({analysis['content_type']}) ===")
    print(f"- {analysis['title']}")
    for point in analysis.get("main_points", []):
        print(f"  * {point}")
    if analysis.get("referenced_topics"):
        print("  Referenced (not explained):")
        for t in analysis["referenced_topics"]:
            print(f"    - {t}")
    if analysis.get("inconsistencies"):
        print("  [!] Inconsistencies:")
        for i in analysis["inconsistencies"]:
            print(f"    - {i}")
    if analysis.get("gaps"):
        print("  Gaps:")
        for g in analysis["gaps"]:
            print(f"    - {g}")


def run(files=None):
    config.require_config()
    log = load_log()

    if files is None:
        files = sorted(
            f
            for f in config.INBOX_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXT and f.name not in log
        )
    else:
        files = sorted(f for f in files if f.name not in log)

    if not files:
        print(f"No new files in {config.INBOX_DIR}")
        return

    for f in files:
        print(f"Processing {f.name} ...")
        try:
            analysis = analyze_file(f)
            page = create_note(analysis, f.name)
            print_report(analysis, f.name)
            print(f"  -> Notion page: {page.get('url')}")

            log[f.name] = {"notion_page_id": page["id"], "processed_at": page["created_time"]}
            save_log(log)

            shutil.move(str(f), str(config.PROCESSED_DIR / f.name))
        except Exception as e:
            print(f"  !! Failed on {f.name}: {e}")


if __name__ == "__main__":
    run()
