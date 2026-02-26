"""
NarratorAgent — Generates plain-English narration of each step for the
user-facing action feed, keeping the user in full control and awareness.
"""

from gemini_client import generate_text

NARRATE_PROMPT_TEMPLATE = """You are a friendly narration agent for a visual workflow assistant called Pilot.
Generate a short, clear, plain-English narration of what just happened.

OVERALL GOAL: {goal}
ACTION PERFORMED: {action_description}
RESULT: {result}

Write a single sentence (max 15 words) that a non-technical user would understand.
Examples:
- "Clicked the 'Edit' button to open the lead record"
- "Typed 'Negotiation' into the Status field"
- "Scrolled down to find the Save button"
- "Opened Gmail in a new tab"

Return ONLY the narration sentence, no quotes, no JSON."""


async def narrate_step(goal: str, action_description: str, result: str) -> str:
    """
    Generate a user-friendly narration for a completed action.

    Args:
        goal: The overall user goal for context
        action_description: What action was just performed
        result: Whether it succeeded and what was observed

    Returns:
        A single plain-English sentence describing the action
    """
    prompt = NARRATE_PROMPT_TEMPLATE.format(
        goal=goal,
        action_description=action_description,
        result=result,
    )

    narration = await generate_text(prompt)

    # Clean up — remove quotes, periods at end if doubled, etc.
    narration = narration.strip().strip('"').strip("'")
    if not narration:
        narration = f"Performed: {action_description}"

    return narration
