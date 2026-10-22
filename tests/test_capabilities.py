"""Capability detection against the real FFmpeg (guards the parsers)."""

from __future__ import annotations

from conftest import requires_ffmpeg
from encodr_mcp.capabilities import available_encoders, available_filters, reset_cache

pytestmark = requires_ffmpeg


async def test_encoder_parser_finds_core_encoders():
    reset_cache()
    enc = await available_encoders()
    # Any usable FFmpeg has these; a broken parser would return an empty set.
    assert "aac" in enc
    assert {"libx264", "png"} & enc


async def test_filter_parser_finds_core_filters():
    reset_cache()
    filters = await available_filters()
    assert len(filters) > 50  # a real build has hundreds; empty => parser broke
    assert {"scale", "fps", "loudnorm"} <= filters


async def test_caches_are_populated_and_resettable():
    await available_encoders()
    import encodr_mcp.capabilities as cap

    assert cap._encoder_cache is not None
    reset_cache()
    assert cap._encoder_cache is None and cap._filter_cache is None
