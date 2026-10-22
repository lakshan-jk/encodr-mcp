"""End-to-end tests that actually invoke ffmpeg. Skipped if ffmpeg is absent."""

from __future__ import annotations

import shutil

import pytest

from encodr_mcp.probe import probe, summarize
from encodr_mcp.runner import run
from encodr_mcp.tools.audio import transcode_audio
from encodr_mcp.tools.image import convert_image
from encodr_mcp.tools.video import remux, transcode_video

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


async def _make_sample(path, *, seconds: int = 1):
    """Synthesize a tiny test clip (color bars + tone)."""
    await run(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={seconds}:size=320x240:rate=15",
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


async def test_probe_reports_streams(tmp_path):
    src = tmp_path / "sample.mp4"
    await _make_sample(src)
    info = summarize(await probe(src))
    assert info["video"] and info["audio"]
    assert info["video"][0]["width"] == 320


async def test_transcode_to_h265(tmp_path):
    src = tmp_path / "sample.mp4"
    await _make_sample(src)
    dst = tmp_path / "out.mp4"
    result = await transcode_video(src, dst, video_codec="h265", crf=28, overwrite=True)
    assert result["media"]["video"][0]["codec"] == "hevc"
    assert result["size_bytes"] > 0


async def test_transcode_audio_to_opus(tmp_path):
    src = tmp_path / "sample.mp4"
    await _make_sample(src)
    dst = tmp_path / "out.opus"
    result = await transcode_audio(src, dst, codec="opus", overwrite=True)
    assert result["media"]["audio"][0]["codec"] == "opus"


async def test_remux_container(tmp_path):
    src = tmp_path / "sample.mp4"
    await _make_sample(src)
    dst = tmp_path / "out.mkv"
    result = await remux(src, dst, overwrite=True)
    assert "matroska" in (result["media"]["format_name"] or "")


async def _make_png(path):
    await run(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=256x256:rate=1",
            "-frames:v",
            "1",
            str(path),
        ]
    )


async def test_image_to_png(tmp_path):
    src = tmp_path / "frame.png"
    await _make_png(src)
    dst = tmp_path / "out_resized.png"
    result = await convert_image(src, dst, fmt="png", width=128, overwrite=True)
    assert result["size_bytes"] > 0
    assert result["media"]["video"][0]["width"] == 128


async def test_image_to_webp_if_supported(tmp_path):
    from encodr_mcp.capabilities import available_encoders

    if "libwebp" not in await available_encoders():
        pytest.skip("this ffmpeg build has no libwebp encoder")
    src = tmp_path / "frame.png"
    await _make_png(src)
    dst = tmp_path / "out.webp"
    result = await convert_image(src, dst, fmt="webp", quality=85, overwrite=True)
    assert result["size_bytes"] > 0


async def test_unsupported_encoder_gives_clear_error(tmp_path):
    from encodr_mcp.capabilities import available_encoders

    if "libwebp" in await available_encoders():
        pytest.skip("libwebp is available; can't test the missing-encoder path")
    src = tmp_path / "frame.png"
    await _make_png(src)
    with pytest.raises(RuntimeError, match="was not compiled with"):
        await convert_image(src, tmp_path / "x.webp", fmt="webp", overwrite=True)
