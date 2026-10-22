"""Audio transcoding operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..capabilities import ensure_encoder
from ..quality import AUDIO_CODECS
from .common import base_input, execute


def build_audio_args(
    src: Path,
    dst: Path,
    *,
    codec: str,
    bitrate: str | None,
    sample_rate: int | None,
    channels: int | None,
    normalize: bool,
    overwrite: bool,
) -> list[str]:
    if codec not in AUDIO_CODECS:
        raise ValueError(f"Unknown audio codec '{codec}'. Choose from {list(AUDIO_CODECS)}.")

    args = base_input(src, overwrite=overwrite)
    args += ["-vn"]  # drop any video/cover-art stream
    if normalize:
        # EBU R128 loudness normalization to -16 LUFS (streaming-friendly).
        args += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    if sample_rate:
        args += ["-ar", str(sample_rate)]
    if channels:
        args += ["-ac", str(channels)]
    args += AUDIO_CODECS[codec].args(bitrate=bitrate)
    args.append(str(dst))
    return args


async def transcode_audio(
    src: Path,
    dst: Path,
    *,
    codec: str = "opus",
    bitrate: str | None = None,
    sample_rate: int | None = None,
    channels: int | None = None,
    normalize: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    if codec not in AUDIO_CODECS:
        raise ValueError(f"Unknown audio codec '{codec}'. Choose from {list(AUDIO_CODECS)}.")
    await ensure_encoder(
        AUDIO_CODECS[codec].encoder, friendly=codec, alternatives=list(AUDIO_CODECS)
    )
    args = build_audio_args(
        src,
        dst,
        codec=codec,
        bitrate=bitrate,
        sample_rate=sample_rate,
        channels=channels,
        normalize=normalize,
        overwrite=overwrite,
    )
    return await execute(args, dst)


def build_extract_audio_args(src: Path, dst: Path, *, overwrite: bool) -> list[str]:
    """Extract the audio track losslessly via stream copy."""
    return [*base_input(src, overwrite=overwrite), "-vn", "-c:a", "copy", str(dst)]


async def extract_audio(src: Path, dst: Path, *, overwrite: bool = False) -> dict[str, Any]:
    return await execute(build_extract_audio_args(src, dst, overwrite=overwrite), dst)
