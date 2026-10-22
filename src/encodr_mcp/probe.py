"""Media inspection via ffprobe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import run


async def probe(path: Path) -> dict[str, Any]:
    """Return ffprobe's full format + stream metadata as a dict."""
    args = [
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = await run(args, binary="ffprobe")
    data: dict[str, Any] = json.loads(result.stdout)
    return data


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    """Condense raw ffprobe output into a compact, LLM-friendly summary."""
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video, audio, subtitle = [], [], []
    for s in streams:
        kind = s.get("codec_type")
        if kind == "video":
            video.append(
                {
                    "index": s.get("index"),
                    "codec": s.get("codec_name"),
                    "profile": s.get("profile"),
                    "width": s.get("width"),
                    "height": s.get("height"),
                    "pix_fmt": s.get("pix_fmt"),
                    "fps": s.get("r_frame_rate"),
                    "bit_rate": s.get("bit_rate"),
                }
            )
        elif kind == "audio":
            audio.append(
                {
                    "index": s.get("index"),
                    "codec": s.get("codec_name"),
                    "channels": s.get("channels"),
                    "sample_rate": s.get("sample_rate"),
                    "bit_rate": s.get("bit_rate"),
                    "language": s.get("tags", {}).get("language"),
                }
            )
        elif kind == "subtitle":
            subtitle.append(
                {
                    "index": s.get("index"),
                    "codec": s.get("codec_name"),
                    "language": s.get("tags", {}).get("language"),
                }
            )
    return {
        "format_name": fmt.get("format_name"),
        "duration_sec": float(fmt["duration"]) if fmt.get("duration") else None,
        "size_bytes": int(fmt["size"]) if fmt.get("size") else None,
        "bit_rate": fmt.get("bit_rate"),
        "video": video,
        "audio": audio,
        "subtitle": subtitle,
    }
