"""
ActionAgent — Translates a planned step into a precise executable action
(click, type, scroll, navigate) with exact coordinates derived from Gemini's
visual understanding of the screenshot.
"""

from gemini_client import analyze_screenshot
import json
import struct

ACTION_PROMPT_TEMPLATE = """You are a precise UI action agent. You need to execute this step:

STEP: {step_description}

The screenshot shows the current state of the web application. It is {width} x {height} pixels.

Determine the EXACT action to perform. Return a JSON object with ONE of these formats:

For clicking:
{{"type": "click", "x": 450, "y": 320, "element_description": "the Edit button"}}

For typing text:
{{"type": "type", "text": "Hello world", "x": 200, "y": 150, "element_description": "the search input field"}}

For scrolling:
{{"type": "scroll", "direction": "down", "amount": 300, "element_description": "the page"}}

For navigating to a URL:
{{"type": "navigate", "url": "https://example.com", "element_description": "navigate to example.com"}}

For pressing a key:
{{"type": "keypress", "key": "Enter", "element_description": "press Enter to submit"}}

IMPORTANT:
- x, y coordinates are in PIXELS from the top-left corner of the screenshot, within 0..{width} and 0..{height}
- Be as precise as possible with coordinates — aim for the CENTER of the target element
- For click actions, identify the exact clickable element (button, link, input field)
- For type actions, click coordinates should target the input field to focus it first

Return ONLY the JSON object, no additional text."""


def png_size(data: bytes):
    """Width and height from a PNG's IHDR header, or None if the bytes are not a PNG."""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


async def determine_action(step_description: str, screenshot_bytes: bytes) -> dict:
    """
    Given a plan step and current screenshot, determine the precise action.

    Args:
        step_description: The planned step (e.g., "Click the 'Edit' button")
        screenshot_bytes: Current tab screenshot as PNG bytes

    Returns:
        dict with type and coordinates/parameters for the action
    """
    size = png_size(screenshot_bytes)
    width, height = size if size else ("unknown", "unknown")
    prompt = ACTION_PROMPT_TEMPLATE.format(step_description=step_description, width=width, height=height)
    result = await analyze_screenshot(screenshot_bytes, prompt)

    # Validate required fields
    action_type = result.get("type", "")
    if action_type not in ("click", "type", "scroll", "navigate", "keypress"):
        return {
            "type": "error",
            "message": f"Unknown action type: {action_type}",
            "raw": result,
        }

    # Ensure coordinate fields are integers where expected
    for coord_key in ("x", "y", "amount"):
        if coord_key in result:
            try:
                result[coord_key] = int(result[coord_key])
            except (ValueError, TypeError):
                pass

    # A click outside the screenshot cannot be the element the model meant; fail the step instead of
    # clicking somewhere arbitrary.
    if size and action_type in ("click", "type"):
        x, y = result.get("x"), result.get("y")
        if not (isinstance(x, int) and isinstance(y, int) and 0 <= x < size[0] and 0 <= y < size[1]):
            return {
                "type": "error",
                "message": f"Coordinates ({x}, {y}) fall outside the {size[0]} x {size[1]} screenshot",
                "raw": result,
            }

    result.setdefault("element_description", "unknown element")
    return result
