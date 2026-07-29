from collections import Counter
from datetime import date

import config
from notion_writer import create_audit_page, get_page_sections, query_recent_pages


def run(days: int = 7):
    config.require_config()
    pages = query_recent_pages(days=days)
    pages = [
        p for p in pages
        if (p["properties"].get("Type", {}).get("select") or {}).get("name") != "Audit"
    ]

    if not pages:
        print("No notes created in the audit window.")
        return

    unused, used = [], []
    all_topics = []
    all_inconsistencies, all_gaps = [], []

    for p in pages:
        title = "".join(rt["plain_text"] for rt in p["properties"]["Name"]["title"])
        used_flag = p["properties"].get("Used", {}).get("checkbox", False)
        untouched_since_creation = p["created_time"] == p["last_edited_time"]

        if used_flag or not untouched_since_creation:
            used.append(title)
        else:
            unused.append(title)

        sections = get_page_sections(p["id"])
        all_topics.extend(sections.get("Referenced Topics", []))
        all_inconsistencies.extend(
            (title, i) for i in sections.get("Inconsistencies", []) if i != "None flagged"
        )
        all_gaps.extend((title, g) for g in sections.get("Gaps", []) if g != "None flagged")

    recurring_topics = [t for t, c in Counter(all_topics).items() if c >= 2]

    report = [f"{len(pages)} notes added this week, {len(unused)} show no sign you opened or used them"]
    for title in unused:
        report.append(f"Unused: {title}")

    if recurring_topics:
        report.append("Topics referenced across multiple sources this week, still unexplained:")
        for t in recurring_topics:
            report.append(f"  - {t}")

    if all_inconsistencies:
        report.append("Inconsistencies flagged this week:")
        for title, i in all_inconsistencies:
            report.append(f"  - [{title}] {i}")

    if all_gaps:
        report.append("Gaps flagged this week:")
        for title, g in all_gaps:
            report.append(f"  - [{title}] {g}")

    print("\n=== WEEKLY AUDIT ===")
    for line in report:
        print(f"* {line}")

    page = create_audit_page(report, date.today().isoformat())
    print(f"\nAudit saved to Notion: {page.get('url')}")


if __name__ == "__main__":
    run()
