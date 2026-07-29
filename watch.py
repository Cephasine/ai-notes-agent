import time
from pathlib import Path

import config
from gemini_analyzer import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from ingest import load_log
from ingest import run as ingest_run

SUPPORTED_EXT = VIDEO_EXT | IMAGE_EXT | AUDIO_EXT

POLL_INTERVAL = 3  # seconds between folder scans
SETTLE_TIME = 2    # seconds a file's size must stay unchanged before it's treated as fully copied


def _is_settled(path: Path) -> bool:
    """Guards against processing a file that's still mid-copy (common with large video drops)."""
    try:
        size_before = path.stat().st_size
    except FileNotFoundError:
        return False

    time.sleep(SETTLE_TIME)

    try:
        size_after = path.stat().st_size
    except FileNotFoundError:
        return False

    return size_before == size_after and size_after > 0


def watch():
    config.require_config()
    print(f"Watching {config.INBOX_DIR} for new files... (Ctrl+C to stop)")
    print(f"Supported: {', '.join(sorted(SUPPORTED_EXT))}\n")

    while True:
        log = load_log()
        candidates = [
            f
            for f in config.INBOX_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXT and f.name not in log
        ]

        if not candidates:
            time.sleep(POLL_INTERVAL)
            continue

        ready = [f for f in candidates if _is_settled(f)]

        if ready:
            ingest_run(files=ready)
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        watch()
    except KeyboardInterrupt:
        print("\nStopped watching.")
