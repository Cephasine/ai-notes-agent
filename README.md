# Content Auditor Agent

Watches/reads/listens to video, image, and audio files, extracts the main
points as bullets, flags inconsistencies/gaps/referenced-but-unexplained
topics, pushes a note to Notion per file, and runs a weekly audit that
reports which notes you never actually touched.

It never edits or rewrites your source material — it only reports.

## 1. Get a Gemini API key

Go to https://aistudio.google.com/apikey and create a key. Free tier is fine
to start.

## 2. Create a Notion integration

1. Go to https://www.notion.so/my-integrations → **New integration**
2. Name it (e.g. "Content Auditor"), pick your workspace, save
3. Copy the **Internal Integration Token** (starts with `secret_` or `ntn_`)

## 3. Create the Notion database

Create a new database (as a full page in Notion) with **exactly** these
properties:

| Property name | Type          |
|----------------|---------------|
| Name           | Title (default) |
| Source         | Text          |
| Type           | Select        |
| Date Added     | Date          |
| Used           | Checkbox      |

You don't need to pre-fill the Select options — the agent creates
`Video` / `Image` / `Audio` / `Audit` options automatically the first
time each one is used.

Then click **`...`** on the database → **Connections** → connect the
integration you just created. (This step is easy to miss — without it
the API gets a 404 on every request.)

## 4. Get the database ID

Open the database as a full page and copy the ID out of the URL:

```
https://www.notion.so/myworkspace/8a1b2c3d4e5f6789...?v=...
                                   ^^^^^^^^^^^^^^^^^^ this part (32 chars)
```

## 5. Install and configure

```bash
cd ai-notes-agent
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in:

```
GEMINI_API_KEY=...
NOTION_TOKEN=...
NOTION_DATABASE_ID=...
```

## 6. Run it

Drop video/image/audio files into the `inbox/` folder, then:

```bash
python ingest.py
```

Each file gets analyzed, a note gets created in Notion, and the file
moves to `processed/` so it's never re-analyzed. A `processed_log.json`
tracks what's been done.

Supported formats:
- Video: mp4, mov, avi, webm, mkv
- Image: jpg, jpeg, png, webp, gif
- Audio: mp3, wav, m4a, aac, ogg, flac, aiff

## 7. Or run it in watch mode (live agent)

Instead of running `ingest.py` by hand every time, leave this running in a
terminal:

```bash
python watch.py
```

It polls the `inbox/` folder every 3 seconds and auto-processes any new
video/image/audio file the moment it's fully copied in — waits for the
file size to stop changing first, so it won't grab a video mid-copy.
Ctrl+C to stop. Good for demos: drop a file in, watch the note appear in
Notion without touching the keyboard again.

## 8. Run the weekly audit

```bash
python audit.py
```

This looks at every note added in the last 7 days and reports:
- Which notes show no sign you opened/edited them since creation (unused)
- Topics referenced across 2+ sources this week that are still unexplained
- Every inconsistency and gap flagged that week

It prints the report as bullets to the terminal **and** creates a
"Weekly Audit" page in the same Notion database.

### Automating the weekly run

**Mac/Linux (cron)** — run every Sunday at 6pm:
```bash
crontab -e
# add this line:
0 18 * * 0 cd /full/path/to/ai-notes-agent && /usr/bin/python3 audit.py >> audit.log 2>&1
```

**Windows (Task Scheduler)**: create a weekly trigger that runs
`python audit.py` with "Start in" set to the project folder.

## How "used" is detected

Notion pages track `created_time` and `last_edited_time` automatically.
If a note's `last_edited_time` still equals its `created_time`, nothing
has touched it since the agent created it — it's marked unused. You can
also manually tick the `Used` checkbox on any note to mark it used
regardless. Note: this only catches edits, not views — opening a page
without changing anything won't register as "used."

## Notes on cost/limits

- Gemini's free tier has per-minute/per-day request limits — fine for a
  contest demo, may need a paid key for heavy volume.
- Large video/audio files go through Gemini's Files API automatically and
  can take a few seconds to a couple minutes to finish processing before
  analysis starts — this is normal, the script waits for it.
