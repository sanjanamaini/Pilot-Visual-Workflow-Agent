"""
PlannerAgent — Breaks a user goal into an ordered sequence of atomic UI actions,
given the current screen state and history of completed steps.
"""

from __future__ import annotations

from gemini_client import generate_text
import json

PLAN_PROMPT_TEMPLATE = """You are a workflow planning agent. The user wants to accomplish a goal by interacting with a web application.

USER GOAL: {goal}

CURRENT UI STATE:
- App: {app_name}
- Page: {page_title}
- Context: {page_context}
- Interactive elements: {elements}

COMPLETED STEPS SO FAR:
{completed_steps}

Create an ordered plan of atomic UI actions to accomplish the user's goal from the current state.
Each step should be a single, specific action (click a button, type text, scroll, navigate).

Return a JSON object:
{{
  "plan": [
    "Step 1: Click the 'Edit' button on the lead record",
    "Step 2: Type 'Negotiation' in the Status dropdown",
    "Step 3: Click the 'Save' button"
  ],
  "reasoning": "Brief explanation of your approach",
  "confidence": 0.85
}}

Be specific about WHICH element to interact with. Reference labels or visible text.
If the goal requires switching to another app/tab, include navigation steps.
Return ONLY the JSON object."""


async def create_plan(goal: str, ui_state: dict, completed_steps: list[str] | None = None) -> dict:
    """
    Generate an action plan for the given goal based on current UI state.

    Args:
        goal: The user's natural-language goal
        ui_state: Output from ScreenInterpreterAgent
        completed_steps: List of already-completed step descriptions

    Returns:
        dict with keys: plan (list[str]), reasoning (str), confidence (float)
    """
    elements_str = json.dumps(ui_state.get("interactive_elements", []), indent=2)
    completed_str = "\n".join(
        f"  ✓ {s}" for s in (completed_steps or [])
    ) or "  (none yet)"

    prompt = PLAN_PROMPT_TEMPLATE.format(
        goal=goal,
        app_name=ui_state.get("app_name", "Unknown"),
        page_title=ui_state.get("page_title", ""),
        page_context=ui_state.get("page_context", ""),
        elements=elements_str,
        completed_steps=completed_str,
    )

    raw = await generate_text(prompt)

    # Parse JSON from response
    try:
        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {
            "plan": [f"Attempt to: {goal}"],
            "reasoning": "Could not parse structured plan, falling back to single-step.",
            "confidence": 0.3,
        }

    result.setdefault("plan", [])
    result.setdefault("reasoning", "")
    result.setdefault("confidence", 0.5)

    return result


async def replan(goal: str, ui_state: dict, failed_step: str, error_observation: str,
                 completed_steps: list[str] | None = None) -> dict:
    """
    Re-plan after a failed step by providing error context.
    """
    augmented_goal = (
        f"{goal}\n\n"
        f"NOTE: The previous attempt to '{failed_step}' failed. "
        f"Observation: {error_observation}. "
        f"Please create an alternative plan that avoids this issue."
    )
    return await create_plan(augmented_goal, ui_state, completed_steps)
