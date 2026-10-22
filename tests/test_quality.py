from encodr_mcp.quality import AUDIO_CODECS, VIDEO_CODECS, image_args


def test_video_codec_default_crf():
    args = VIDEO_CODECS["h264"].args()
    assert "-c:v" in args and "libx264" in args
    assert args[args.index("-crf") + 1] == "18"


def test_video_codec_crf_override():
    args = VIDEO_CODECS["h265"].args(crf=24)
    assert args[args.index("-crf") + 1] == "24"


def test_audio_lossless_has_no_bitrate():
    args = AUDIO_CODECS["flac"].args()
    assert "-b:a" not in args


def test_audio_bitrate_override():
    args = AUDIO_CODECS["opus"].args(bitrate="256k")
    assert args[args.index("-b:a") + 1] == "256k"


def test_image_png_has_no_quality_flag():
    assert image_args("png") == ["-c:v", "png"]


def test_image_webp_quality():
    args = image_args("webp", quality=80)
    assert args[args.index("-quality") + 1] == "80"
