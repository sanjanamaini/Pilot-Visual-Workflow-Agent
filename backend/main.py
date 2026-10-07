"""
Pilot Backend -- FastAPI server with WebSocket endpoint.
Orchestrates the 5-agent pipeline: Interpreter -> Planner -> Action -> Verifier -> Narrator
"""

import asyncio
import base64
import io
import json
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from session_manager import (
    Session,
    StepResult,
    create_session,
    get_or_create_session,
    get_session,
    update_session,
    add_step_result,
)
from agents.screen_interpreter import interpret_screen
from agents.planner import create_plan, replan
from agents.action_agent import determine_action
from agents.verifier import verify_action
from agents.narrator import narrate_step

# A failed step triggers a replan from the current screen. Without a cap, a step that keeps failing
# replans forever, each round costing four model calls; after this many replans the goal fails.
MAX_REPLANS = 3


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Pilot] Backend starting...")
    yield
    print("[Pilot] Backend shutting down...")


app = FastAPI(
    title="Pilot — Visual Workflow Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

class GoalRequest(BaseModel):
    goal: str


class SessionResponse(BaseModel):
    session_id: str
    status: str
    goal: str
    plan: list[str]
    completed_steps: int
    current_step_index: int


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pilot-backend"}


@app.post("/session/start")
async def start_session():
    session = create_session()
    return {"session_id": session.session_id, "status": session.status}


@app.get("/session/{session_id}/status")
async def session_status(session_id: str):
    session = get_session(session_id)
    if session is None:
        return {"error": "Session not found"}
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        goal=session.goal,
        plan=session.plan,
        completed_steps=len(session.completed_steps),
        current_step_index=session.current_step_index,
    )


# ---------------------------------------------------------------------------
# WebSocket — real-time agent pipeline
# ---------------------------------------------------------------------------

async def send_json(ws: WebSocket, msg: dict):
    """Send a JSON message over the WebSocket."""
    await ws.send_text(json.dumps(msg))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await ws.accept()
    session = get_or_create_session(session_id)

    await send_json(ws, {
        "type": "connected",
        "session_id": session.session_id,
        "message": "Pilot is ready. Send a goal to get started.",
    })

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "goal":
                # User sends a new goal
                goal = data.get("goal", "")
                update_session(session_id, goal=goal, status="planning", plan=[], current_step_index=0, replan_count=0)
                session = get_session(session_id)

                await send_json(ws, {
                    "type": "status",
                    "status": "planning",
                    "message": f"Got it! Planning how to: {goal}",
                })

                # We need a screenshot first — ask the extension to send one
                await send_json(ws, {"type": "request_screenshot"})

            elif msg_type == "screenshot":
                # Extension sends a base64 screenshot
                screenshot_b64 = data.get("image", "")
                if not screenshot_b64:
                    continue

                screenshot_bytes = base64.b64decode(screenshot_b64)
                update_session(session_id, last_screenshot_b64=screenshot_b64)
                session = get_session(session_id)

                if session.status == "planning":
                    # Run the full pipeline: interpret → plan → execute steps
                    await run_agent_pipeline(ws, session, screenshot_bytes)

                elif session.status == "executing":
                    # Mid-execution screenshot — verify last action & continue
                    await continue_execution(ws, session, screenshot_bytes)

                elif session.status == "verifying":
                    # Verification screenshot
                    await verify_and_continue(ws, session, screenshot_bytes)

            elif msg_type == "stop":
                update_session(session_id, status="idle")
                await send_json(ws, {
                    "type": "status",
                    "status": "stopped",
                    "message": "Workflow stopped by user.",
                })

            elif msg_type == "pause":
                update_session(session_id, status="paused")
                await send_json(ws, {
                    "type": "status",
                    "status": "paused",
                    "message": "Workflow paused. Send 'resume' to continue.",
                })

            elif msg_type == "resume":
                if session.status == "paused":
                    update_session(session_id, status="executing")
                    await send_json(ws, {"type": "request_screenshot"})

    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        # Windows-safe traceback printing
        tb = traceback.format_exc()
        safe_tb = tb.encode('ascii', errors='replace').decode('ascii')
        print(f"[ERROR] WebSocket handler crashed:\n{safe_tb}")
        try:
            err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            await send_json(ws, {
                "type": "error",
                "message": f"Internal error: {err_msg}",
            })
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Agent pipeline orchestration
# ---------------------------------------------------------------------------

async def run_agent_pipeline(ws: WebSocket, session: Session, screenshot_bytes: bytes):
    """Full pipeline: interpret screen -> create plan -> start executing."""
    session_id = session.session_id
    print(f"[Pipeline] Starting for session {session_id}, screenshot {len(screenshot_bytes)} bytes")

    # Step 1: Interpret the screen
    await send_json(ws, {
        "type": "narration",
        "step": -1,
        "message": "Analyzing the current screen...",
        "status": "running",
    })

    try:
        print("[Pipeline] Calling interpret_screen...")
        ui_state = await interpret_screen(screenshot_bytes)
        print(f"[Pipeline] interpret_screen returned: {list(ui_state.keys()) if isinstance(ui_state, dict) else type(ui_state)}")
    except Exception as e:
        err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
        print(f"[Pipeline] interpret_screen FAILED: {err_msg}")
        await send_json(ws, {
            "type": "narration",
            "step": -1,
            "message": f"Screen analysis failed: {err_msg}",
            "status": "failed",
        })
        update_session(session_id, status="failed")
        return

    await send_json(ws, {
        "type": "narration",
        "step": -1,
        "message": f"I see {ui_state.get('app_name', 'a web application')} — {ui_state.get('page_context', 'analyzing the page')}",
        "status": "done",
    })

    # Step 2: Create a plan
    await send_json(ws, {
        "type": "narration",
        "step": -1,
        "message": "Creating an action plan...",
        "status": "running",
    })

    plan_result = await create_plan(session.goal, ui_state)
    plan_steps = plan_result.get("plan", [])

    update_session(session_id, plan=plan_steps, status="executing", current_step_index=0)

    await send_json(ws, {
        "type": "plan",
        "steps": plan_steps,
        "reasoning": plan_result.get("reasoning", ""),
        "confidence": plan_result.get("confidence", 0.5),
    })

    # Step 3: Execute the first step
    if plan_steps:
        await execute_current_step(ws, session_id, screenshot_bytes)
    else:
        update_session(session_id, status="completed")
        await send_json(ws, {
            "type": "status",
            "status": "completed",
            "message": "No actions needed — goal appears already achieved!",
        })


async def execute_current_step(ws: WebSocket, session_id: str, screenshot_bytes: bytes):
    """Execute the current step in the plan."""
    session = get_session(session_id)
    if session is None or session.current_step_index >= len(session.plan):
        update_session(session_id, status="completed")
        await send_json(ws, {
            "type": "status",
            "status": "completed",
            "message": "All steps completed! ✅",
        })
        return

    step_desc = session.plan[session.current_step_index]
    step_idx = session.current_step_index

    await send_json(ws, {
        "type": "narration",
        "step": step_idx,
        "message": f"Working on: {step_desc}",
        "status": "running",
    })

    # Determine the precise action
    action = await determine_action(step_desc, screenshot_bytes)

    if action.get("type") == "error":
        await send_json(ws, {
            "type": "narration",
            "step": step_idx,
            "message": f"Could not determine action: {action.get('message', 'unknown error')}",
            "status": "failed",
        })
        update_session(session_id, status="failed")
        return

    # Send the action to the extension for execution
    update_session(session_id, status="verifying")
    await send_json(ws, {
        "type": "execute_action",
        "action": action,
        "step_index": step_idx,
        "step_description": step_desc,
    })

    # Wait a moment, then request a verification screenshot
    await asyncio.sleep(1.5)
    await send_json(ws, {"type": "request_screenshot"})


async def verify_and_continue(ws: WebSocket, session: Session, screenshot_bytes: bytes):
    """Verify the last action and continue to the next step."""
    session_id = session.session_id
    step_idx = session.current_step_index
    step_desc = session.plan[step_idx] if step_idx < len(session.plan) else "unknown step"

    # Verify
    verification = await verify_action(
        action_description=step_desc,
        expected_outcome=f"The UI should reflect the completion of: {step_desc}",
        screenshot_bytes=screenshot_bytes,
    )

    # Narrate
    narration = await narrate_step(
        goal=session.goal,
        action_description=step_desc,
        result=verification.get("observation", ""),
    )

    success = verification.get("success", False)

    # Record the step result
    add_step_result(session_id, StepResult(
        step_index=step_idx,
        action_description=step_desc,
        success=success,
        narration=narration,
    ))

    await send_json(ws, {
        "type": "narration",
        "step": step_idx,
        "message": narration,
        "status": "done" if success else "failed",
    })

    if success:
        # Move to next step
        session = get_session(session_id)
        update_session(session_id, status="executing")
        await execute_current_step(ws, session_id, screenshot_bytes)
    elif verification.get("should_replan", False) and get_session(session_id).replan_count >= MAX_REPLANS:
        update_session(session_id, status="failed")
        await send_json(ws, {
            "type": "status",
            "status": "failed",
            "message": f"Stopped after {MAX_REPLANS} replans: {verification.get('observation', 'the step keeps failing')}",
        })
    elif verification.get("should_replan", False):
        # Replan
        update_session(session_id, replan_count=get_session(session_id).replan_count + 1)
        await send_json(ws, {
            "type": "narration",
            "step": step_idx,
            "message": "Step didn't work as expected — replanning...",
            "status": "running",
        })

        ui_state = await interpret_screen(screenshot_bytes)
        completed = [s.action_description for s in session.completed_steps if s.success]
        new_plan = await replan(
            session.goal, ui_state, step_desc,
            verification.get("observation", ""), completed,
        )

        new_steps = new_plan.get("plan", [])
        update_session(session_id, plan=new_steps, current_step_index=0, status="executing")

        await send_json(ws, {
            "type": "plan",
            "steps": new_steps,
            "reasoning": new_plan.get("reasoning", "Replanned after failure"),
            "confidence": new_plan.get("confidence", 0.5),
        })

        if new_steps:
            await execute_current_step(ws, session_id, screenshot_bytes)
        else:
            update_session(session_id, status="failed")
            await send_json(ws, {
                "type": "status",
                "status": "failed",
                "message": "Could not find an alternative approach. Please try a different command.",
            })
    else:
        update_session(session_id, status="failed")
        await send_json(ws, {
            "type": "status",
            "status": "failed",
            "message": f"Step failed: {verification.get('observation', 'unknown reason')}",
        })


async def continue_execution(ws: WebSocket, session: Session, screenshot_bytes: bytes):
    """Resume execution with a fresh screenshot."""
    await execute_current_step(ws, session.session_id, screenshot_bytes)


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
