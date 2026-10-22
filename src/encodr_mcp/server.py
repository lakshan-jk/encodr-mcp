"""MCP server exposing FFmpeg transcoding tools over stdio.

Works with any MCP host (Claude Desktop, Claude Code, etc.). Each tool resolves
and validates its paths, then delegates to the ``tools`` package.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .paths import PathError, resolve_input, resolve_output
from .probe import probe as _probe
from .probe import summarize
from .quality import AUDIO_CODECS, IMAGE_FORMATS, VIDEO_CODECS
from .runner import FFmpegError
from .tools import audio, image, streams, video

mcp = MCPServer("encodr-mcp")

_R = TypeVar("_R")


def friendly_errors(fn: Callable[..., Awaitable[_R]]) -> Callable[..., Awaitable[_R]]:
    """Convert expected domain errors into ``ToolError`` so their helpful message
    (codec lists, path hints, missing-encoder notes) survives to the model instead
    of being flattened into a generic "unexpected error"."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> _R:
        try:
            return await fn(*args, **kwargs)
        except (PathError, ValueError, FFmpegError, RuntimeError) as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


@mcp.tool()
@friendly_errors
async def probe_media(path: str) -> dict[str, Any]:
    """Inspect a media file and return a compact summary of its format and streams."""
    src = resolve_input(path)
    return summarize(await _probe(src))


@mcp.tool()
@friendly_errors
async def list_codecs() -> dict[str, Any]:
    """List the supported video/audio codecs and image formats with their quality defaults."""
    return {
        "video": {
            k: {"encoder": v.encoder, "default_crf": v.default_crf} for k, v in VIDEO_CODECS.items()
        },
        "audio": {
            k: {"encoder": v.encoder, "default_bitrate": v.default_bitrate}
            for k, v in AUDIO_CODECS.items()
        },
        "image": {
            k: {"encoder": str(v["encoder"]), "default_quality": v["default_quality"]}
            for k, v in IMAGE_FORMATS.items()
        },
    }


@mcp.tool()
@friendly_errors
async def transcode_video(
    input: str,
    output: str,
    video_codec: str = "h264",
    audio_codec: str = "aac",
    crf: int | None = None,
    preset: str | None = None,
    scale_height: int | None = None,
    fps: int | None = None,
    audio_bitrate: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Transcode a video. Quality is CRF-based (lower crf = higher quality).

    Codecs: h264 (default, universal), h265, av1 (best compression), vp9.
    Optionally downscale with scale_height (e.g. 1080) or change fps.
    """
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await video.transcode_video(
        src,
        dst,
        video_codec=video_codec,
        audio_codec=audio_codec,
        crf=crf,
        preset=preset,
        scale_height=scale_height,
        fps=fps,
        audio_bitrate=audio_bitrate,
        overwrite=overwrite,
    )


@mcp.tool()
@friendly_errors
async def remux_video(input: str, output: str, overwrite: bool = False) -> dict[str, Any]:
    """Change a video's container (e.g. .mkv -> .mp4) with no re-encode. Lossless and fast."""
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await video.remux(src, dst, overwrite=overwrite)


@mcp.tool()
@friendly_errors
async def transcode_audio(
    input: str,
    output: str,
    codec: str = "opus",
    bitrate: str | None = None,
    sample_rate: int | None = None,
    channels: int | None = None,
    normalize: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Transcode audio. Codecs: opus (default), aac, mp3, flac (lossless), wav.

    Set normalize=true for EBU R128 loudness normalization (-16 LUFS).
    """
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await audio.transcode_audio(
        src,
        dst,
        codec=codec,
        bitrate=bitrate,
        sample_rate=sample_rate,
        channels=channels,
        normalize=normalize,
        overwrite=overwrite,
    )


@mcp.tool()
@friendly_errors
async def extract_audio(input: str, output: str, overwrite: bool = False) -> dict[str, Any]:
    """Extract the audio track from a video losslessly (stream copy)."""
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await audio.extract_audio(src, dst, overwrite=overwrite)


@mcp.tool()
@friendly_errors
async def convert_image(
    input: str,
    output: str,
    fmt: str,
    quality: int | None = None,
    width: int | None = None,
    height: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Convert/resize an image. Formats: webp, avif, jpeg, png (lossless).

    For webp/jpeg, quality is 0-100; for avif, quality is a CRF-like value.
    """
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await image.convert_image(
        src, dst, fmt=fmt, quality=quality, width=width, height=height, overwrite=overwrite
    )


@mcp.tool()
@friendly_errors
async def thumbnail(
    input: str, output: str, at: str = "00:00:01", width: int | None = None, overwrite: bool = False
) -> dict[str, Any]:
    """Grab a single high-quality frame from a video at timestamp `at` (HH:MM:SS)."""
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await streams.thumbnail(src, dst, at=at, width=width, overwrite=overwrite)


@mcp.tool()
@friendly_errors
async def burn_subtitles(
    input: str, subtitles: str, output: str, overwrite: bool = False
) -> dict[str, Any]:
    """Burn (hardcode) a subtitle file into the video. Audio is copied unchanged."""
    src = resolve_input(input)
    subs = resolve_input(subtitles)
    dst = resolve_output(output, overwrite=overwrite)
    return await streams.burn_subtitles(src, subs, dst, overwrite=overwrite)


@mcp.tool()
@friendly_errors
async def extract_stream(
    input: str, output: str, index: int, overwrite: bool = False
) -> dict[str, Any]:
    """Extract a single stream (by absolute index from probe_media) losslessly."""
    src = resolve_input(input)
    dst = resolve_output(output, overwrite=overwrite)
    return await streams.extract_stream(src, dst, index=index, overwrite=overwrite)


def run() -> None:
    """Run the server over stdio (the default MCP transport)."""
    mcp.run(transport="stdio")
