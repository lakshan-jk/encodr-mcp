"""Shared helpers for building and finalizing ffmpeg jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..probe import probe, summarize
from ..runner import run


def base_input(path: Path, *, overwrite: bool) -> list[str]:
    """Standard leading args: quiet logging, overwrite policy, then input."""
    return ["-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n", "-i", str(path)]


async def execute(args: list[str], output: Path, *, timeout: float = 3600) -> dict[str, Any]:
    """Run an ffmpeg job and return a structured summary of the output."""
    await run(args, binary="ffmpeg", timeout=timeout)
    info = summarize(await probe(output))
    return {
        "output": str(output),
        "size_bytes": output.stat().st_size,
        "media": info,
    }
