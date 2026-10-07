"""
Replan-cap tests for the orchestration loop in main.py.

Every model call is replaced by a stub, so these run without a GOOGLE_API_KEY:
    cd backend && python -m unittest discover tests
"""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import WebSocketDisconnect  # noqa: E402

import main  # noqa: E402
from session_manager import _sessions, create_session, get_session, update_session  # noqa: E402


class FakeWS:
    """Records what the backend sends; replays scripted client messages."""

    def __init__(self, incoming=()):
        self.sent = []
        self.incoming = list(incoming)

    async def accept(self):
        pass

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def receive_text(self):
        if not self.incoming:
            raise WebSocketDisconnect()
        return json.dumps(self.incoming.pop(0))


async def no_sleep(_seconds):
    pass


def start_stubs(test, verdicts):
    """Patch every agent call; the verifier returns the given verdicts in turn (the last one repeats)."""
    seq = list(verdicts)

    async def verify(**_kw):
        return dict(seq.pop(0) if len(seq) > 1 else seq[0])

    async def narrate(**_kw):
        return "narration"

    async def interpret(_bytes):
        return {"app_name": "Test app"}

    async def replan(*_a, **_kw):
        return {"plan": ["click Save"], "reasoning": "try again"}

    async def act(_step, _bytes):
        return {"type": "click", "x": 10, "y": 10}

    for name, fn in (("verify_action", verify), ("narrate_step", narrate), ("interpret_screen", interpret),
                     ("replan", replan), ("determine_action", act)):
        mock.patch.object(main, name, side_effect=fn).start()
    mock.patch.object(main.asyncio, "sleep", side_effect=no_sleep).start()
    test.addCleanup(mock.patch.stopall)


async def drive(ws, session_id, max_rounds=50):
    """Answer every screenshot request until the session leaves 'verifying' (or max_rounds is hit)."""
    rounds = 0
    while get_session(session_id).status == "verifying" and rounds < max_rounds:
        await main.verify_and_continue(ws, get_session(session_id), b"png")
        rounds += 1
    return rounds


class ReplanCapTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _sessions.clear()
        self.sid = create_session("s1").session_id
        update_session(self.sid, goal="Save the form", plan=["click Save"], status="executing")

    async def test_step_that_always_fails_stops_after_cap(self):
        start_stubs(self, [{"success": False, "should_replan": True, "observation": "Save button not found"}])
        ws = FakeWS()
        await main.execute_current_step(ws, self.sid, b"png")
        rounds = await drive(ws, self.sid)

        self.assertEqual(get_session(self.sid).status, "failed")
        self.assertEqual(main.replan.call_count, main.MAX_REPLANS)
        self.assertEqual(rounds, main.MAX_REPLANS + 1)  # the original attempt plus one per replan
        self.assertEqual(ws.sent[-1]["status"], "failed")
        self.assertIn(f"Stopped after {main.MAX_REPLANS} replans", ws.sent[-1]["message"])

    async def test_without_the_cap_the_loop_never_ends(self):
        # The pre-fix behaviour: lift the cap and the same failing step replans until the test's own guard stops it.
        start_stubs(self, [{"success": False, "should_replan": True, "observation": "Save button not found"}])
        ws = FakeWS()
        with mock.patch.object(main, "MAX_REPLANS", 10 ** 9):
            await main.execute_current_step(ws, self.sid, b"png")
            rounds = await drive(ws, self.sid, max_rounds=50)

        self.assertEqual(rounds, 50)
        self.assertEqual(get_session(self.sid).status, "verifying")

    async def test_recovery_within_cap_completes(self):
        fail = {"success": False, "should_replan": True, "observation": "no change"}
        start_stubs(self, [fail, {"success": True, "observation": "saved"}])
        ws = FakeWS()
        await main.execute_current_step(ws, self.sid, b"png")
        await drive(ws, self.sid)

        self.assertEqual(get_session(self.sid).status, "completed")
        self.assertEqual(get_session(self.sid).replan_count, 1)

    async def test_failure_without_replan_flag_fails_immediately(self):
        start_stubs(self, [{"success": False, "should_replan": False, "observation": "blocked by a login wall"}])
        ws = FakeWS()
        await main.execute_current_step(ws, self.sid, b"png")
        await drive(ws, self.sid)

        self.assertEqual(get_session(self.sid).status, "failed")
        self.assertEqual(main.replan.call_count, 0)

    async def test_new_goal_resets_the_count(self):
        update_session(self.sid, replan_count=main.MAX_REPLANS, status="failed")
        ws = FakeWS(incoming=[{"type": "goal", "goal": "Open settings"}])
        await main.websocket_endpoint(ws, self.sid)

        self.assertEqual(get_session(self.sid).replan_count, 0)
        self.assertEqual(get_session(self.sid).status, "planning")


if __name__ == "__main__":
    unittest.main()
