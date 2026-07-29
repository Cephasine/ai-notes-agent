import contextlib
import io
import tempfile
from pathlib import Path

from flask import Flask, Response, request

import config
from audit import run as run_audit
from gemini_analyzer import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, analyze_file
from notion_writer import create_note

app = Flask(__name__)

SUPPORTED_EXT = VIDEO_EXT | IMAGE_EXT | AUDIO_EXT

UPLOAD_PAGE = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Content Auditor</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 480px; margin: 40px auto; padding: 0 20px; background:#111; color:#eee; }
  h1 { font-size: 1.3rem; }
  input[type=file] { display:block; margin: 20px 0; width:100%; color:#eee; }
  button { width:100%; padding: 14px; font-size:1rem; background:#4f8cff; color:white; border:none; border-radius:8px; }
  button:disabled { background:#555; }
  #status { margin-top: 20px; white-space: pre-wrap; font-size: 0.9rem; line-height:1.4; }
</style>
</head>
<body>
<h1>Drop content to audit</h1>
<form id="f">
  <input type="file" name="file" accept="video/*,image/*,audio/*" required>
  <button type="submit" id="btn">Analyze &amp; send to Notion</button>
</form>
<div id="status"></div>
<script>
const form = document.getElementById('f');
const status = document.getElementById('status');
const btn = document.getElementById('btn');
const key = new URLSearchParams(window.location.search).get('key') || '';

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true;
  status.textContent = 'Uploading + analyzing... can take up to a couple minutes for video, longer if the server was asleep.';
  const data = new FormData(form);
  try {
    const resp = await fetch('/upload?key=' + encodeURIComponent(key), { method: 'POST', body: data });
    const text = await resp.text();
    status.textContent = text;
  } catch (err) {
    status.textContent = 'Error: ' + err;
  } finally {
    btn.disabled = false;
  }
});
</script>
</body>
</html>
"""


def _authorized() -> bool:
    key = request.args.get("key", "")
    return bool(config.UPLOAD_SECRET) and key == config.UPLOAD_SECRET


@app.route("/", methods=["GET"])
def home():
    return Response(UPLOAD_PAGE, mimetype="text/html")


@app.route("/upload", methods=["POST"])
def upload():
    if not _authorized():
        return Response("Forbidden: missing or wrong ?key=", status=403)

    f = request.files.get("file")
    if not f or not f.filename:
        return Response("No file received", status=400)

    ext = Path(f.filename).suffix.lower()
    if ext not in SUPPORTED_EXT:
        return Response(f"Unsupported file type: {ext}", status=400)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        analysis = analyze_file(tmp_path)
        page = create_note(analysis, f.filename)
    except Exception as e:
        return Response(f"Failed: {e}", status=500)
    finally:
        tmp_path.unlink(missing_ok=True)

    lines = [f"Saved: {analysis['title']}", ""]
    lines += [f"* {p}" for p in analysis.get("main_points", [])]
    if analysis.get("inconsistencies"):
        lines.append("\n[!] Inconsistencies:")
        lines += [f"- {i}" for i in analysis["inconsistencies"]]
    if analysis.get("gaps"):
        lines.append("\nGaps:")
        lines += [f"- {g}" for g in analysis["gaps"]]
    lines.append(f"\nNotion: {page.get('url', '')}")

    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/audit", methods=["GET"])
def audit_endpoint():
    if not _authorized():
        return Response("Forbidden: missing or wrong ?key=", status=403)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_audit()
    return Response(buf.getvalue() or "No output", mimetype="text/plain")


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
