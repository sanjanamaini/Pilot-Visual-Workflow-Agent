"""
Gemini 2.5 Pro client wrapper for Pilot.
Handles multimodal (image + text) and text-only calls.
"""

import os
import json
import base64
import asyncio
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Client initialization
# ---------------------------------------------------------------------------
_client: Optional[genai.Client] = None

MODEL_ID = "gemini-2.5-pro"


def _get_client() -> genai.Client:
    """Lazy-init the GenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY environment variable is not set. "
                "Get one at https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

async def analyze_screenshot(image_bytes: bytes, prompt: str) -> dict:
    """
    Send a screenshot + text prompt to Gemini 2.5 Pro (multimodal).
    Returns the parsed JSON dict from the model response.
    """
    client = _get_client()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    text_part = types.Part.from_text(text=prompt)

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_ID,
        contents=[types.Content(parts=[image_part, text_part])],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    # Strip markdown fences if the model wraps its response
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # remove opening fence
        raw = raw.rsplit("```", 1)[0]  # remove closing fence
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_text": raw}


async def generate_text(prompt: str) -> str:
    """
    Text-only call to Gemini 2.5 Pro (e.g. narration, planning).
    Returns the raw text response.
    """
    client = _get_client()

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_ID,
        contents=[types.Content(parts=[types.Part.from_text(text=prompt)])],
        config=types.GenerateContentConfig(
            temperature=0.4,
        ),
    )

    return response.text.strip()
