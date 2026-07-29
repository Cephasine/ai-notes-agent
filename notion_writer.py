from datetime import date, datetime, timedelta, timezone

import requests

import config

HEADERS = {
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": config.NOTION_VERSION,
}

SECTION_HEADINGS = ["Main Points", "Referenced Topics", "Inconsistencies", "Gaps"]


def _bullet_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
    }


def _heading(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _bullets(items, empty_note: str) -> list:
    items = items or []
    if not items:
        return [_bullet_block(empty_note)]
    return [_bullet_block(t) for t in items]


def create_note(analysis: dict, source_filename: str) -> dict:
    """Creates a Notion page from a Gemini analysis dict. Returns the created page object."""
    properties = {
        "Name": {"title": [{"text": {"content": analysis["title"][:200]}}]},
        "Source": {"rich_text": [{"text": {"content": source_filename}}]},
        "Type": {"select": {"name": analysis["content_type"].capitalize()}},
        "Date Added": {"date": {"start": date.today().isoformat()}},
        "Used": {"checkbox": False},
    }

    children = [
        _heading("Main Points"),
        *_bullets(analysis.get("main_points"), "No clear main points extracted"),
        _heading("Referenced Topics"),
        *_bullets(analysis.get("referenced_topics"), "None referenced"),
        _heading("Inconsistencies"),
        *_bullets(analysis.get("inconsistencies"), "None flagged"),
        _heading("Gaps"),
        *_bullets(analysis.get("gaps"), "None flagged"),
    ]

    payload = {
        "parent": {"database_id": config.NOTION_DATABASE_ID},
        "properties": properties,
        "children": children,
    }
    resp = requests.post(f"{config.NOTION_API_BASE}/pages", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def query_recent_pages(days: int = 7) -> list:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    payload = {"filter": {"property": "Date Added", "date": {"on_or_after": start}}}
    resp = requests.post(
        f"{config.NOTION_API_BASE}/databases/{config.NOTION_DATABASE_ID}/query",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def get_page_sections(page_id: str) -> dict:
    """Pulls the bullet text back out from under each heading, for audit aggregation."""
    resp = requests.get(f"{config.NOTION_API_BASE}/blocks/{page_id}/children", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    blocks = resp.json().get("results", [])

    sections = {h: [] for h in SECTION_HEADINGS}
    current = None
    for block in blocks:
        btype = block.get("type")
        if btype == "heading_3":
            text = "".join(rt["plain_text"] for rt in block["heading_3"]["rich_text"])
            current = text if text in sections else None
        elif btype == "bulleted_list_item" and current:
            text = "".join(rt["plain_text"] for rt in block["bulleted_list_item"]["rich_text"])
            sections[current].append(text)
    return sections


def create_audit_page(report_lines: list, week_label: str) -> dict:
    properties = {
        "Name": {"title": [{"text": {"content": f"Weekly Audit - {week_label}"}}]},
        "Type": {"select": {"name": "Audit"}},
        "Date Added": {"date": {"start": date.today().isoformat()}},
        "Used": {"checkbox": True},
    }
    children = [_bullet_block(line) for line in report_lines] or [_bullet_block("Nothing to report")]
    payload = {
        "parent": {"database_id": config.NOTION_DATABASE_ID},
        "properties": properties,
        "children": children,
    }
    resp = requests.post(f"{config.NOTION_API_BASE}/pages", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
