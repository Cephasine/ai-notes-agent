import json
import time
from pathlib import Path

from google import genai
from google.genai import types

import config

MODEL = "gemini-3.5-flash"

SYSTEM_INSTRUCTION = """You are a strict content auditor, not an editor or a summarizer-for-publication.
You watch/read/listen to source material and report on it. You never rewrite, rephrase for style,
polish, or "improve" the content. You extract facts and structure only.

Rules:
- Output concise bullet points. Never write paragraphs.
- main_points: the core takeaways, as short standalone bullets. No fluff, no restating the prompt.
- referenced_topics: names, concepts, tools, events, or claims the source MENTIONS but does not explain.
  These are leads for the person to go look up themselves - do not explain them yourself.
- inconsistencies: contradictions, unsupported claims, or moments where the source disagrees with itself.
  Be specific about what conflicts with what.
- gaps: missing context, unanswered questions the material itself raises, or steps it skips.
- Do not pad any list with weak or invented entries just to fill it. Empty lists are fine and expected.
"""

ANALYSIS_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "title": types.Schema(type=types.Type.STRING, description="Short descriptive title, 8 words max"),
        "content_type": types.Schema(type=types.Type.STRING, enum=["video", "image", "audio"]),
        "main_points": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "referenced_topics": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "inconsistencies": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "gaps": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
    },
    required=["title", "content_type", "main_points", "referenced_topics", "inconsistencies", "gaps"],
)

VIDEO_EXT = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".aiff"}


def guess_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in IMAGE_EXT:
        return "image"
    if ext in AUDIO_EXT:
        return "audio"
    raise ValueError(f"Unsupported file type: {ext}")


def _wait_until_active(client, uploaded_file, max_wait_seconds: int = 120):
    waited = 0
    while getattr(uploaded_file, "state", None) is None or uploaded_file.state.name == "PROCESSING":
        if waited >= max_wait_seconds:
            raise TimeoutError("Gemini file processing timed out.")
        time.sleep(3)
        waited += 3
        uploaded_file = client.files.get(name=uploaded_file.name)
    if uploaded_file.state.name == "FAILED":
        raise RuntimeError("Gemini failed to process the uploaded file.")
    return uploaded_file


def analyze_file(filepath: Path) -> dict:
    """Uploads a video/image/audio file to Gemini and returns a structured report dict."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    content_type = guess_content_type(filepath)

    uploaded = client.files.upload(file=str(filepath))
    uploaded = _wait_until_active(client, uploaded)

    prompt = (
        f"This is a {content_type} file. Analyze it and return the structured report "
        f"described in your instructions. Report only - do not edit, rewrite, or improve "
        f"the source content. Bullets only."
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ANALYSIS_SCHEMA,
        ),
    )

    data = json.loads(response.text)
    data.setdefault("content_type", content_type)
    return data
