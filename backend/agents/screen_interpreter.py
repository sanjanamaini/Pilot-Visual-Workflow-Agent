"""
ScreenInterpreterAgent — Analyzes a screenshot to produce a structured
understanding of the current UI state using Gemini 3.1 Pro multimodal.
"""

from gemini_client import analyze_screenshot

INTERPRET_PROMPT = """You are a UI analysis agent. Analyze this screenshot and return a JSON object with:

{
  "app_name": "Name of the application visible (e.g. Salesforce, Gmail, Notion)",
  "page_title": "The title or heading of the current page/view",
  "visible_data": ["List of key data items visible on screen"],
  "interactive_elements": [
    {
      "type": "button | link | input | dropdown | checkbox | tab | menu_item",
      "label": "The text label of the element",
      "bbox": {"x": 100, "y": 200, "width": 80, "height": 30},
      "state": "enabled | disabled | selected | checked | unchecked"
    }
  ],
  "page_context": "Brief description of what the user appears to be doing",
  "notable_text": ["Important text or data values visible on screen"]
}

Be precise with bounding box coordinates. Estimate pixel positions relative to the
top-left corner of the screenshot. Only include clearly visible interactive elements.
Return ONLY the JSON object, no additional text."""


async def interpret_screen(screenshot_bytes: bytes) -> dict:
    """
    Analyze a screenshot and return a structured UI state.

    Args:
        screenshot_bytes: PNG image bytes of the current tab

    Returns:
        dict with keys: app_name, page_title, visible_data,
        interactive_elements, page_context, notable_text
    """
    result = await analyze_screenshot(screenshot_bytes, INTERPRET_PROMPT)

    # Ensure expected keys exist with defaults
    defaults = {
        "app_name": "Unknown",
        "page_title": "",
        "visible_data": [],
        "interactive_elements": [],
        "page_context": "",
        "notable_text": [],
    }
    for key, default in defaults.items():
        result.setdefault(key, default)

    return result
