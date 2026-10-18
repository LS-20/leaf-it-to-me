"""The only place that talks to an LLM. Every result is cached on disk.

Gemini (Google AI Studio key in .env as GEMINI_API_KEY). One call per input.
"""
import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

load_dotenv(ROOT / ".env")
_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY missing: add it to .env")
        _client = genai.Client(api_key=key)
    return _client


def call_llm(prompt: str, schema=None, image: bytes | None = None,
             image_mime: str = "image/jpeg"):
    """Return parsed JSON. Cached by hash of (model, prompt, image, schema)."""
    h = hashlib.sha256()
    for part in (MODEL, prompt, json.dumps(schema, sort_keys=True, default=str)):
        h.update(part.encode())
    if image:
        h.update(image)
    path = CACHE / f"{h.hexdigest()[:32]}.json"
    if path.exists():
        return json.loads(path.read_text())

    from google.genai import types
    contents = [prompt]
    if image:
        contents.insert(0, types.Part.from_bytes(data=image, mime_type=image_mime))
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0,
    )
    for attempt in range(3):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL, contents=contents, config=config)
            break
        except Exception as e:  # rate limit or transient error
            if attempt == 2 or "429" not in str(e) and "503" not in str(e):
                raise
            time.sleep(2 ** attempt * 5)
    data = json.loads(resp.text)
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=1))
    return data
