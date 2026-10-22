"""Stream-level operations: subtitles, thumbnails, and stream extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..capabilities import ensure_filter
from .common import base_input, execute


def build_thumbnail_args(
    src: Path, dst: Path, *, at: str, width: int | None, overwrite: bool
) -> list[str]:
    # -ss before -i seeks fast (keyframe-accurate enough for a thumbnail).
    args = [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y" if overwrite else "-n",
        "-ss",
        at,
        "-i",
        str(src),
    ]
    if width:
        args += ["-vf", f"scale={width}:-2"]
    args += ["-frames:v", "1", "-q:v", "2", str(dst)]
    return args


async def thumbnail(
    src: Path, dst: Path, *, at: str = "00:00:01", width: int | None = None, overwrite: bool = False
) -> dict[str, Any]:
    return await execute(
        build_thumbnail_args(src, dst, at=at, width=width, overwrite=overwrite), dst
    )


def build_burn_subtitles_args(src: Path, subs: Path, dst: Path, *, overwrite: bool) -> list[str]:
    # Escape characters special to the subtitles filter (notably ':' on paths).
    escaped = str(subs).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return [
        *base_input(src, overwrite=overwrite),
        "-vf",
        f"subtitles='{escaped}'",
        "-c:a",
        "copy",
        str(dst),
    ]


async def burn_subtitles(
    src: Path, subs: Path, dst: Path, *, overwrite: bool = False
) -> dict[str, Any]:
    await ensure_filter("subtitles", needed_for="Burning subtitles", requires="libass")
    return await execute(build_burn_subtitles_args(src, subs, dst, overwrite=overwrite), dst)


def build_extract_stream_args(src: Path, dst: Path, *, index: int, overwrite: bool) -> list[str]:
    """Copy a single stream (by absolute index) into its own file, losslessly."""
    return [*base_input(src, overwrite=overwrite), "-map", f"0:{index}", "-c", "copy", str(dst)]


async def extract_stream(
    src: Path, dst: Path, *, index: int, overwrite: bool = False
) -> dict[str, Any]:
    return await execute(build_extract_stream_args(src, dst, index=index, overwrite=overwrite), dst)
