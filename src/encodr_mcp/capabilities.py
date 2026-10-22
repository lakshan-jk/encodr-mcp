"""Runtime detection of which encoders the installed FFmpeg actually supports.

FFmpeg builds vary wildly (a muxer may exist without its encoder, codecs may be
omitted by the packager). Rather than fail deep inside a transcode, we query the
encoder list once, cache it, and validate choices up front with a helpful error.
"""

from __future__ import annotations

from .runner import run

_encoder_cache: set[str] | None = None
_filter_cache: set[str] | None = None


async def available_encoders() -> set[str]:
    """Return the set of encoder names this FFmpeg supports (cached)."""
    global _encoder_cache
    if _encoder_cache is None:
        result = await run(["-hide_banner", "-encoders"], binary="ffmpeg")
        encoders: set[str] = set()
        for line in result.stdout.splitlines():
            # Lines look like: " V....D libx264  H.264 ...". The flags token is
            # followed by the encoder name.
            parts = line.split()
            if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
                encoders.add(parts[1])
        _encoder_cache = encoders
    return _encoder_cache


async def ensure_encoder(encoder: str, *, friendly: str, alternatives: list[str]) -> None:
    """Raise a clear error if ``encoder`` is unavailable in this FFmpeg build."""
    available = await available_encoders()
    if encoder not in available:
        usable = [a for a in alternatives if a != friendly]
        hint = f" Available here: {', '.join(usable)}." if usable else ""
        raise RuntimeError(
            f"'{friendly}' requires the '{encoder}' encoder, which this FFmpeg build "
            f"was not compiled with.{hint}"
        )


async def available_filters() -> set[str]:
    """Return the set of filter names this FFmpeg supports (cached)."""
    global _filter_cache
    if _filter_cache is None:
        result = await run(["-hide_banner", "-filters"], binary="ffmpeg")
        filters: set[str] = set()
        for line in result.stdout.splitlines():
            # Lines look like: " ... subtitles  V->V  Render text subtitles ...".
            # The name is the second whitespace token after the flags column.
            parts = line.split()
            # A real filter row: a short flags column (chars from TSC.) then the
            # name then an arrows column like "A->A" / "V->V" / "N->N".
            if (
                len(parts) >= 3
                and 1 <= len(parts[0]) <= 3
                and set(parts[0]) <= set("TSC.")
                and "->" in parts[2]
            ):
                filters.add(parts[1])
        _filter_cache = filters
    return _filter_cache


async def ensure_filter(name: str, *, needed_for: str, requires: str) -> None:
    """Raise a clear error if filter ``name`` is unavailable in this FFmpeg build."""
    if name not in await available_filters():
        raise RuntimeError(
            f"{needed_for} needs the '{name}' filter, which this FFmpeg build lacks "
            f"(it must be compiled with {requires})."
        )


def reset_cache() -> None:
    """Clear the cached encoder/filter sets (used in tests)."""
    global _encoder_cache, _filter_cache
    _encoder_cache = None
    _filter_cache = None
