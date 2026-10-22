"""Video transcoding operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..capabilities import ensure_encoder
from ..quality import AUDIO_CODECS, VIDEO_CODECS
from .common import base_input, execute


def build_transcode_args(
    src: Path,
    dst: Path,
    *,
    video_codec: str,
    audio_codec: str,
    crf: int | None,
    preset: str | None,
    scale_height: int | None,
    fps: int | None,
    audio_bitrate: str | None,
    overwrite: bool,
) -> list[str]:
    if video_codec not in VIDEO_CODECS:
        raise ValueError(f"Unknown video codec '{video_codec}'. Choose from {list(VIDEO_CODECS)}.")
    if audio_codec not in AUDIO_CODECS:
        raise ValueError(f"Unknown audio codec '{audio_codec}'. Choose from {list(AUDIO_CODECS)}.")

    args = base_input(src, overwrite=overwrite)
    vfilters = []
    if scale_height:
        # -2 keeps width even and preserves aspect ratio.
        vfilters.append(f"scale=-2:{scale_height}")
    if fps:
        vfilters.append(f"fps={fps}")
    if vfilters:
        args += ["-vf", ",".join(vfilters)]

    args += VIDEO_CODECS[video_codec].args(crf=crf, preset=preset)
    args += AUDIO_CODECS[audio_codec].args(bitrate=audio_bitrate)
    args.append(str(dst))
    return args


async def transcode_video(
    src: Path,
    dst: Path,
    *,
    video_codec: str = "h264",
    audio_codec: str = "aac",
    crf: int | None = None,
    preset: str | None = None,
    scale_height: int | None = None,
    fps: int | None = None,
    audio_bitrate: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    if video_codec not in VIDEO_CODECS:
        raise ValueError(f"Unknown video codec '{video_codec}'. Choose from {list(VIDEO_CODECS)}.")
    if audio_codec not in AUDIO_CODECS:
        raise ValueError(f"Unknown audio codec '{audio_codec}'. Choose from {list(AUDIO_CODECS)}.")
    await ensure_encoder(
        VIDEO_CODECS[video_codec].encoder, friendly=video_codec, alternatives=list(VIDEO_CODECS)
    )
    await ensure_encoder(
        AUDIO_CODECS[audio_codec].encoder, friendly=audio_codec, alternatives=list(AUDIO_CODECS)
    )
    args = build_transcode_args(
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
    return await execute(args, dst)


def build_remux_args(src: Path, dst: Path, *, overwrite: bool) -> list[str]:
    """Change container without re-encoding (stream copy) — lossless, instant."""
    return [*base_input(src, overwrite=overwrite), "-c", "copy", str(dst)]


async def remux(src: Path, dst: Path, *, overwrite: bool = False) -> dict[str, Any]:
    return await execute(build_remux_args(src, dst, overwrite=overwrite), dst)
