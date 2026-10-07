"""
Session manager for Pilot.
In-memory store for development; swap to Firestore for production.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    step_index: int
    action_description: str
    action: dict = Field(default_factory=dict)
    success: bool = False
    narration: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    plan: list[str] = Field(default_factory=list)
    completed_steps: list[StepResult] = Field(default_factory=list)
    current_step_index: int = 0
    status: str = "idle"  # idle | planning | executing | paused | completed | failed
    replan_count: int = 0  # replans used for the current goal (capped in main.MAX_REPLANS)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_screenshot_b64: Optional[str] = None


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_sessions: dict[str, Session] = {}


def create_session(session_id: Optional[str] = None) -> Session:
    session = Session(session_id=session_id or str(uuid.uuid4()))
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Optional[Session]:
    return _sessions.get(session_id)


def get_or_create_session(session_id: str) -> Session:
    if session_id not in _sessions:
        return create_session(session_id)
    return _sessions[session_id]


def update_session(session_id: str, **kwargs) -> Optional[Session]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)
    return session


def add_step_result(session_id: str, result: StepResult) -> Optional[Session]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    session.completed_steps.append(result)
    session.current_step_index = result.step_index + 1
    return session


def delete_session(session_id: str) -> bool:
    return _sessions.pop(session_id, None) is not None
