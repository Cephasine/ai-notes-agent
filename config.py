import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

BASE_DIR = Path(__file__).resolve().parent
INBOX_DIR = Path(os.getenv("INBOX_DIR", BASE_DIR / "inbox"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", BASE_DIR / "processed"))
LOG_FILE = BASE_DIR / "processed_log.json"

NOTION_VERSION = "2026-03-11"
NOTION_API_BASE = "https://api.notion.com/v1"

for _d in (INBOX_DIR, PROCESSED_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def require_config():
    missing = [
        name
        for name, val in [
            ("GEMINI_API_KEY", GEMINI_API_KEY),
            ("NOTION_TOKEN", NOTION_TOKEN),
            ("NOTION_DATABASE_ID", NOTION_DATABASE_ID),
        ]
        if not val
    ]
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}.\n"
            f"Copy .env.example to .env and fill them in."
        )
