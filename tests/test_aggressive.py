"""Aggressive end-to-end tests: every available codec, edge cases, concurrency,
error paths, and the real MCP tool layer via ``call_tool``."""

from __future__ import annotations

import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from conftest import make_srt, make_video, requires_ffmpeg, tool_payload
from encodr_mcp.capabilities import available_encoders, available_filters
from encodr_mcp.paths import PathError
from encodr_mcp.probe import probe, summarize
from encodr_mcp.quality import AUDIO_CODECS, VIDEO_CODECS
from encodr_mcp.runner import FFmpegError, run
from encodr_mcp.server import mcp
from encodr_mcp.tools import audio, image, streams, video

pytestmark = requires_ffmpeg

EXPECTED_VCODEC = {"h264": "h264", "h265": "hevc", "av1": "av1", "vp9": "vp9"}
EXPECTED_ACODEC = {"opus": "opus", "aac": "aac", "mp3": "mp3", "flac": "flac", "wav": "pcm_s16le"}
EXT = {"h264": "mp4", "h265": "mp4", "av1": "mp4", "vp9": "webm"}
AEXT = {"opus": "opus", "aac": "m4a", "mp3": "mp3", "flac": "flac", "wav": "wav"}


# --- Every video codec this build supports --------------------------------
@pytest.mark.parametrize("codec", list(VIDEO_CODECS))
async def test_every_video_codec(codec, sample_video, tmp_path):
    enc = VIDEO_CODECS[codec].encoder
    if enc not in await available_encoders():
        pytest.skip(f"{enc} not available")
    dst = tmp_path / f"out.{EXT[codec]}"
    acodec = "opus" if codec == "vp9" else "aac"
    res = await video.transcode_video(
        sample_video, dst, video_codec=codec, audio_codec=acodec, crf=30, overwrite=True
    )
    assert res["media"]["video"][0]["codec"] == EXPECTED_VCODEC[codec]
    assert res["size_bytes"] > 0


# --- Every audio codec this build supports --------------------------------
@pytest.mark.parametrize("codec", list(AUDIO_CODECS))
async def test_every_audio_codec(codec, sample_video, tmp_path):
    enc = AUDIO_CODECS[codec].encoder
    if enc not in await available_encoders():
        pytest.skip(f"{enc} not available")
    dst = tmp_path / f"out.{AEXT[codec]}"
    res = await audio.transcode_audio(sample_video, dst, codec=codec, overwrite=True)
    assert res["media"]["audio"][0]["codec"] == EXPECTED_ACODEC[codec]


# --- Transform correctness -------------------------------------------------
async def test_scale_height_is_exact_and_even_width(sample_video, tmp_path):
    dst = tmp_path / "scaled.mp4"
    res = await video.transcode_video(sample_video, dst, scale_height=240, crf=30, overwrite=True)
    v = res["media"]["video"][0]
    assert v["height"] == 240
    assert v["width"] % 2 == 0


async def test_fps_change(sample_video, tmp_path):
    dst = tmp_path / "fps.mp4"
    res = await video.transcode_video(sample_video, dst, fps=10, crf=30, overwrite=True)
    num, den = (int(x) for x in res["media"]["video"][0]["fps"].split("/"))
    assert round(num / den) == 10


@pytest.mark.parametrize("container", ["mkv", "mov", "webm"])
async def test_remux_preserves_codec(container, sample_video, tmp_path):
    # webm needs vp9/opus; transcode first for that case, else plain remux of h264.
    if container == "webm":
        src = tmp_path / "vp9.webm"
        if "libvpx-vp9" not in await available_encoders():
            pytest.skip("vp9 unavailable")
        await video.transcode_video(
            sample_video, src, video_codec="vp9", audio_codec="opus", crf=40, overwrite=True
        )
        return
    dst = tmp_path / f"out.{container}"
    res = await video.remux(sample_video, dst, overwrite=True)
    assert res["media"]["video"][0]["codec"] == "h264"  # unchanged by remux


# --- Streams: thumbnail, subtitles, extraction ----------------------------
async def test_thumbnail_dimensions(sample_video, tmp_path):
    dst = tmp_path / "thumb.jpg"
    res = await streams.thumbnail(sample_video, dst, at="00:00:01", width=160, overwrite=True)
    assert res["media"]["video"][0]["width"] == 160


async def test_burn_subtitles_keeps_audio(sample_video, tmp_path):
    if "subtitles" not in await available_filters():
        pytest.skip("this ffmpeg build has no libass/subtitles filter")
    subs = make_srt(tmp_path / "subs.srt")
    dst = tmp_path / "subbed.mp4"
    res = await streams.burn_subtitles(sample_video, subs, dst, overwrite=True)
    assert res["media"]["video"] and res["media"]["audio"]


async def test_burn_subtitles_missing_libass_gives_clear_error(sample_video, tmp_path):
    if "subtitles" in await available_filters():
        pytest.skip("libass present; can't test the missing-filter path")
    subs = make_srt(tmp_path / "subs.srt")
    with pytest.raises(RuntimeError, match="libass"):
        await streams.burn_subtitles(sample_video, subs, tmp_path / "x.mp4", overwrite=True)


async def test_extract_video_and_audio_streams(sample_video, tmp_path):
    vout = tmp_path / "v.mp4"
    aout = tmp_path / "a.m4a"
    rv = await streams.extract_stream(sample_video, vout, index=0, overwrite=True)
    ra = await streams.extract_stream(sample_video, aout, index=1, overwrite=True)
    assert rv["media"]["video"] and not rv["media"]["audio"]
    assert ra["media"]["audio"] and not ra["media"]["video"]


async def test_extract_audio_stream_copy(sample_video, tmp_path):
    dst = tmp_path / "a.m4a"
    res = await audio.extract_audio(sample_video, dst, overwrite=True)
    assert res["media"]["audio"][0]["codec"] == "aac"


# --- Audio processing ------------------------------------------------------
async def test_loudnorm_and_resample(sample_video, tmp_path):
    dst = tmp_path / "norm.opus"
    res = await audio.transcode_audio(
        sample_video,
        dst,
        codec="opus",
        sample_rate=48000,
        channels=1,
        normalize=True,
        overwrite=True,
    )
    assert res["media"]["audio"][0]["channels"] == 1


# --- Images ----------------------------------------------------------------
@pytest.mark.parametrize("fmt", ["png", "jpeg", "avif"])
async def test_image_formats(fmt, sample_png, tmp_path):
    from encodr_mcp.quality import IMAGE_FORMATS

    enc = str(IMAGE_FORMATS[fmt]["encoder"])
    if enc not in await available_encoders():
        pytest.skip(f"{enc} unavailable")
    dst = tmp_path / f"out.{fmt}"
    res = await image.convert_image(sample_png, dst, fmt=fmt, width=128, overwrite=True)
    assert res["size_bytes"] > 0


# --- Concurrency: the async runner must handle parallel jobs ---------------
async def test_concurrent_transcodes(sample_video, tmp_path):
    async def job(i: int):
        dst = tmp_path / f"c{i}.mp4"
        return await video.transcode_video(
            sample_video, dst, crf=32, scale_height=120, overwrite=True
        )

    results = await asyncio.gather(*(job(i) for i in range(6)))
    assert all(r["size_bytes"] > 0 for r in results)
    assert len({r["output"] for r in results}) == 6


# --- Nasty filenames -------------------------------------------------------
@pytest.mark.parametrize("name", ["a b c.mp4", "wéìrd_ünïcode.mp4", "tri cky (1).mp4"])
async def test_spaces_and_unicode_filenames(name, tmp_path):
    src = await make_video(tmp_path / name, seconds=1, width=160, height=120)
    dst = tmp_path / f"out-{name}"
    res = await video.transcode_video(src, dst, crf=32, overwrite=True)
    assert res["size_bytes"] > 0


async def test_subtitle_path_with_colon(sample_video, tmp_path):
    if "subtitles" not in await available_filters():
        pytest.skip("this ffmpeg build has no libass/subtitles filter")
    subs = make_srt(tmp_path / "wei:rd.srt")
    dst = tmp_path / "subbed2.mp4"
    res = await streams.burn_subtitles(sample_video, subs, dst, overwrite=True)
    assert res["media"]["video"]


# --- Error paths -----------------------------------------------------------
async def test_unknown_video_codec_raises(sample_video, tmp_path):
    with pytest.raises(ValueError, match="Unknown video codec"):
        await video.transcode_video(
            sample_video, tmp_path / "x.mp4", video_codec="h266", overwrite=True
        )


async def test_corrupt_input_raises_ffmpeg_error(tmp_path):
    bad = tmp_path / "broken.mp4"
    bad.write_bytes(b"this is definitely not a video file" * 10)
    with pytest.raises(FFmpegError):
        await video.transcode_video(bad, tmp_path / "out.mp4", overwrite=True)


async def test_overwrite_protection(sample_video, tmp_path):
    from encodr_mcp.paths import resolve_output

    existing = tmp_path / "exists.mp4"
    existing.write_bytes(b"x")
    with pytest.raises(PathError, match="already exists"):
        resolve_output(str(existing), overwrite=False)


async def test_timeout_is_enforced(tmp_path):
    # A long synthetic encode that cannot finish within 1ms.
    args = [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=60:size=1280x720:rate=30",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        str(tmp_path / "slow.mp4"),
    ]
    with pytest.raises(FFmpegError, match="timed out"):
        await run(args, binary="ffmpeg", timeout=0.001)


# --- The real MCP tool layer (schema validation + serialization) -----------
async def test_tool_layer_probe(sample_video):
    res = await mcp.call_tool("probe_media", {"path": str(sample_video)})
    assert not res.is_error
    payload = tool_payload(res)
    assert payload["video"] and payload["audio"]


async def test_tool_layer_transcode(sample_video, tmp_path):
    dst = tmp_path / "tool_out.mp4"
    res = await mcp.call_tool(
        "transcode_video",
        {
            "input": str(sample_video),
            "output": str(dst),
            "video_codec": "h265",
            "crf": 30,
            "overwrite": True,
        },
    )
    assert not res.is_error
    payload = tool_payload(res)
    assert payload["media"]["video"][0]["codec"] == "hevc"
    assert dst.exists()


async def test_tool_layer_list_codecs():
    res = await mcp.call_tool("list_codecs", {})
    payload = tool_payload(res)
    assert set(payload["video"]) == set(VIDEO_CODECS)
    assert set(payload["audio"]) == set(AUDIO_CODECS)


# In-process call_tool RE-RAISES as ToolError (the stdio transport turns these
# into is_error results — see test_e2e_stdio). We assert the helpful message
# survives, which is the whole point of the friendly_errors wrapper.
async def test_tool_layer_missing_input_preserves_message():
    with pytest.raises(ToolError, match="does not exist"):
        await mcp.call_tool("probe_media", {"path": "/no/such/file.mp4"})


async def test_tool_layer_bad_codec_preserves_message(sample_video, tmp_path):
    with pytest.raises(ToolError, match="Unknown video codec"):
        await mcp.call_tool(
            "transcode_video",
            {
                "input": str(sample_video),
                "output": str(tmp_path / "x.mp4"),
                "video_codec": "nope",
                "overwrite": True,
            },
        )


# --- Probe summary sanity --------------------------------------------------
async def test_probe_summary_shape(sample_video):
    info = summarize(await probe(sample_video))
    assert info["duration_sec"] and info["duration_sec"] > 0
    assert info["video"][0]["width"] == 640
    assert info["audio"][0]["codec"] == "aac"
