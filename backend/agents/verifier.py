"""
VerifierAgent — After each action, receives a fresh screenshot and verifies
the action succeeded before proceeding. If the UI didn't change as expected,
signals for replanning.
"""

from gemini_client import analyze_screenshot

VERIFY_PROMPT_TEMPLATE = """You are a UI verification agent. An automated action was just performed on a web application.

ACTION PERFORMED: {action_description}
EXPECTED OUTCOME: {expected_outcome}

Look at this screenshot taken AFTER the action was executed. Determine if the action succeeded.

Return a JSON object:
{{
  "success": true,
  "observation": "The status field now shows 'Negotiation' as expected",
  "should_replan": false,
  "confidence": 0.9
}}

Guidelines:
- "success": true if the UI reflects the expected change
- "observation": describe what you actually see in the current state
- "should_replan": true if the action clearly failed and a different approach is needed
- "confidence": 0.0 to 1.0 how confident you are in your assessment

If the page is loading or transitioning, set success=true with lower confidence.
Return ONLY the JSON object."""


async def verify_action(
    action_description: str,
    expected_outcome: str,
    screenshot_bytes: bytes,
) -> dict:
    """
    Verify that an executed action produced the expected result.

    Args:
        action_description: What action was performed
        expected_outcome: What should have changed in the UI
        screenshot_bytes: Screenshot taken after the action

    Returns:
        dict with success, observation, should_replan, confidence
    """
    prompt = VERIFY_PROMPT_TEMPLATE.format(
        action_description=action_description,
        expected_outcome=expected_outcome,
    )

    result = await analyze_screenshot(screenshot_bytes, prompt)

    # Defaults
    result.setdefault("success", False)
    result.setdefault("observation", "No observation available")
    result.setdefault("should_replan", not result["success"])
    result.setdefault("confidence", 0.5)

    return result
