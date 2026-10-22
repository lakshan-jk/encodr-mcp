"""Shared fixtures + media synthesis helpers for the test suite."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import pytest_asyncio

from encodr_mcp.runner import run

HAVE_FFMPEG = shutil.which("ffmpeg") is not None
requires_ffmpeg = pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")


async def make_video(
    path: Path, *, seconds: int = 2, width: int = 640, height: int = 480, rate: int = 24
) -> Path:
    """Synthesize a test clip (color bars + 440Hz tone, H.264/AAC in MP4)."""
    await run(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={seconds}:size={width}x{height}:rate={rate}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ]
    )
    return path


async def make_png(path: Path, *, size: int = 256) -> Path:
    await run(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration=1:size={size}x{size}:rate=1",
            "-frames:v",
            "1",
            str(path),
        ]
    )
    return path


def make_srt(path: Path) -> Path:
    path.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\nHello encodr-mcp\n\n"
        "2\n00:00:01,500 --> 00:00:02,000\nSecond line\n",
        encoding="utf-8",
    )
    return path


def tool_payload(result: object) -> dict:
    """Extract the dict payload from an MCP CallToolResult (structured or JSON text)."""
    sc = getattr(result, "structured_content", None)
    if sc:
        return sc
    content = getattr(result, "content", None) or []
    if content and hasattr(content[0], "text"):
        return json.loads(content[0].text)
    raise AssertionError(f"no payload in result: {result!r}")


@pytest_asyncio.fixture
async def sample_video(tmp_path: Path) -> Path:
    return await make_video(tmp_path / "sample.mp4")


@pytest_asyncio.fixture
async def sample_png(tmp_path: Path) -> Path:
    return await make_png(tmp_path / "frame.png")
