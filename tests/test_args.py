from pathlib import Path

import pytest

from encodr_mcp.tools.audio import build_audio_args
from encodr_mcp.tools.image import build_image_args
from encodr_mcp.tools.streams import build_burn_subtitles_args, build_thumbnail_args
from encodr_mcp.tools.video import build_remux_args, build_transcode_args

SRC = Path("/in/clip.mkv")
DST = Path("/out/clip.mp4")


def test_transcode_builds_scale_and_fps_filters():
    args = build_transcode_args(
        SRC,
        DST,
        video_codec="h264",
        audio_codec="aac",
        crf=20,
        preset=None,
        scale_height=720,
        fps=30,
        audio_bitrate=None,
        overwrite=True,
    )
    vf = args[args.index("-vf") + 1]
    assert "scale=-2:720" in vf and "fps=30" in vf
    assert args[-1] == str(DST)
    assert "-y" in args and "-i" in args


def test_transcode_rejects_unknown_codec():
    with pytest.raises(ValueError, match="Unknown video codec"):
        build_transcode_args(
            SRC,
            DST,
            video_codec="h266",
            audio_codec="aac",
            crf=None,
            preset=None,
            scale_height=None,
            fps=None,
            audio_bitrate=None,
            overwrite=False,
        )


def test_remux_is_stream_copy():
    args = build_remux_args(SRC, DST, overwrite=False)
    assert "-c" in args and args[args.index("-c") + 1] == "copy"
    assert "-n" in args  # no overwrite


def test_audio_normalize_adds_loudnorm():
    args = build_audio_args(
        SRC,
        Path("/out/a.opus"),
        codec="opus",
        bitrate=None,
        sample_rate=48000,
        channels=2,
        normalize=True,
        overwrite=True,
    )
    assert any("loudnorm" in a for a in args)
    assert args[args.index("-ar") + 1] == "48000"


def test_image_avif_forces_muxer():
    args = build_image_args(
        SRC, Path("/out/x.avif"), fmt="avif", quality=None, width=512, height=None, overwrite=True
    )
    assert args[args.index("-f") + 1] == "avif"
    assert "scale=512:-2" in args[args.index("-vf") + 1]


def test_thumbnail_seeks_before_input():
    args = build_thumbnail_args(SRC, Path("/out/t.jpg"), at="00:01:00", width=320, overwrite=True)
    assert args.index("-ss") < args.index("-i")
    assert args[args.index("-frames:v") + 1] == "1"


def test_burn_subtitles_escapes_path():
    args = build_burn_subtitles_args(SRC, Path("/subs/my:file.srt"), DST, overwrite=True)
    vf = args[args.index("-vf") + 1]
    assert "\\:" in vf  # colon escaped for the subtitles filter
