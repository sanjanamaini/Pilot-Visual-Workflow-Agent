"""
Action-agent tests: the prompt states the screenshot size, and coordinates outside it are rejected.
No model calls: analyze_screenshot is stubbed.
"""

import os
import struct
import sys
import unittest
import zlib
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import action_agent  # noqa: E402


def tiny_png(width, height):
    """A valid PNG header (signature + IHDR chunk) for the given size; enough for png_size."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    return b"\x89PNG\r\n\x1a\n" + chunk


class PngSizeTest(unittest.TestCase):
    def test_reads_retina_sized_capture(self):
        self.assertEqual(action_agent.png_size(tiny_png(2880, 1800)), (2880, 1800))

    def test_non_png_returns_none(self):
        self.assertIsNone(action_agent.png_size(b"\xff\xd8\xff\xe0 not a png"))


class BoundsTest(unittest.IsolatedAsyncioTestCase):
    async def run_with(self, reply):
        seen = {}

        async def fake(_bytes, prompt):
            seen["prompt"] = prompt
            return dict(reply)

        with mock.patch.object(action_agent, "analyze_screenshot", side_effect=fake):
            out = await action_agent.determine_action("Click Save", tiny_png(1440, 900))
        return out, seen["prompt"]

    async def test_prompt_states_size(self):
        _, prompt = await self.run_with({"type": "click", "x": 10, "y": 10})
        self.assertIn("1440 x 900 pixels", prompt)

    async def test_inside_passes(self):
        out, _ = await self.run_with({"type": "click", "x": "720", "y": 450})
        self.assertEqual((out["type"], out["x"], out["y"]), ("click", 720, 450))

    async def test_outside_is_an_error(self):
        out, _ = await self.run_with({"type": "click", "x": 1600, "y": 450})
        self.assertEqual(out["type"], "error")
        self.assertIn("outside the 1440 x 900", out["message"])

    async def test_scroll_needs_no_coordinates(self):
        out, _ = await self.run_with({"type": "scroll", "direction": "down", "amount": 300})
        self.assertEqual(out["type"], "scroll")


if __name__ == "__main__":
    unittest.main()
