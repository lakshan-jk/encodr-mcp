"""Image conversion operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..capabilities import ensure_encoder
from ..quality import IMAGE_FORMATS, image_args
from .common import base_input, execute


def build_image_args(
    src: Path,
    dst: Path,
    *,
    fmt: str,
    quality: int | None,
    width: int | None,
    height: int | None,
    overwrite: bool,
) -> list[str]:
    if fmt not in IMAGE_FORMATS:
        raise ValueError(f"Unknown image format '{fmt}'. Choose from {list(IMAGE_FORMATS)}.")

    args = base_input(src, overwrite=overwrite)
    if width or height:
        w = width if width else -2
        h = height if height else -2
        args += ["-vf", f"scale={w}:{h}"]
    # AVIF is written through the avif muxer; force it explicitly.
    if fmt == "avif":
        args += ["-f", "avif"]
    args += image_args(fmt, quality=quality)
    args += ["-frames:v", "1", str(dst)]
    return args


async def convert_image(
    src: Path,
    dst: Path,
    *,
    fmt: str,
    quality: int | None = None,
    width: int | None = None,
    height: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    if fmt not in IMAGE_FORMATS:
        raise ValueError(f"Unknown image format '{fmt}'. Choose from {list(IMAGE_FORMATS)}.")
    await ensure_encoder(
        str(IMAGE_FORMATS[fmt]["encoder"]), friendly=fmt, alternatives=list(IMAGE_FORMATS)
    )
    args = build_image_args(
        src, dst, fmt=fmt, quality=quality, width=width, height=height, overwrite=overwrite
    )
    return await execute(args, dst)
