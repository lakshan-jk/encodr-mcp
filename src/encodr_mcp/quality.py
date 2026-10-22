"""Codec presets encoding a "no compromise on quality" default policy.

Every preset is CRF/quality-based (constant *quality*, variable bitrate) rather
than fixed-bitrate, which gives the best quality-per-byte. Defaults target
visually-transparent or near-transparent output; callers may override.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VideoCodec:
    name: str
    encoder: str
    #: Lower CRF = higher quality. Sensible visually-near-lossless default.
    default_crf: int
    crf_flag: str = "-crf"
    #: Extra args appended verbatim (pixel format, profile, speed preset, ...).
    extra: tuple[str, ...] = ()

    def args(self, crf: int | None = None, preset: str | None = None) -> list[str]:
        out = [
            "-c:v",
            self.encoder,
            self.crf_flag,
            str(crf if crf is not None else self.default_crf),
        ]
        if preset:
            out += ["-preset", preset]
        out += list(self.extra)
        return out


@dataclass(frozen=True, slots=True)
class AudioCodec:
    name: str
    encoder: str
    #: None => lossless, no bitrate flag.
    default_bitrate: str | None
    extra: tuple[str, ...] = ()

    def args(self, bitrate: str | None = None) -> list[str]:
        out = ["-c:a", self.encoder]
        chosen = bitrate if bitrate is not None else self.default_bitrate
        if chosen is not None:
            out += ["-b:a", chosen]
        out += list(self.extra)
        return out


# --- Video -----------------------------------------------------------------
# yuv420p keeps output playable everywhere; faststart helps web/progressive
# playback by moving the moov atom to the front.
VIDEO_CODECS: dict[str, VideoCodec] = {
    "h264": VideoCodec(
        "h264",
        "libx264",
        default_crf=18,
        extra=(
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-movflags",
            "+faststart",
        ),
    ),
    "h265": VideoCodec(
        "h265",
        "libx265",
        default_crf=20,
        extra=(
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-tag:v",
            "hvc1",
            "-movflags",
            "+faststart",
        ),
    ),
    "av1": VideoCodec(
        "av1",
        "libsvtav1",
        default_crf=28,
        extra=("-preset", "6", "-pix_fmt", "yuv420p", "-movflags", "+faststart"),
    ),
    "vp9": VideoCodec(
        "vp9",
        "libvpx-vp9",
        default_crf=30,
        extra=("-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2"),
    ),
}

# --- Audio -----------------------------------------------------------------
AUDIO_CODECS: dict[str, AudioCodec] = {
    "opus": AudioCodec("opus", "libopus", default_bitrate="160k", extra=("-vbr", "on")),
    "aac": AudioCodec("aac", "aac", default_bitrate="192k"),
    "mp3": AudioCodec("mp3", "libmp3lame", default_bitrate="320k", extra=("-q:a", "0")),
    "flac": AudioCodec("flac", "flac", default_bitrate=None, extra=("-compression_level", "8")),
    "wav": AudioCodec("wav", "pcm_s16le", default_bitrate=None),
}

# --- Images ----------------------------------------------------------------
# For images, "quality" is encoder-specific. These map a format to its encoder
# and a quality-flag builder. Higher quality value = better (0-100) for the
# lossy formats; PNG is always lossless.
IMAGE_FORMATS: dict[str, dict[str, object]] = {
    "webp": {"encoder": "libwebp", "quality_flag": "-quality", "default_quality": 90},
    "avif": {"encoder": "libsvtav1", "quality_flag": "-crf", "default_quality": 23, "invert": True},
    "jpeg": {"encoder": "mjpeg", "quality_flag": "-q:v", "default_quality": 2, "invert": True},
    "png": {"encoder": "png", "quality_flag": None, "default_quality": None},
}


def image_args(fmt: str, quality: int | None = None) -> list[str]:
    spec = IMAGE_FORMATS[fmt]
    out = ["-c:v", str(spec["encoder"])]
    flag = spec["quality_flag"]
    if flag is not None:
        q = quality if quality is not None else spec["default_quality"]
        out += [str(flag), str(q)]
    return out


@dataclass(slots=True)
class Capabilities:
    """Which codecs the installed ffmpeg actually supports (filled at runtime)."""

    video: list[str] = field(default_factory=list)
    audio: list[str] = field(default_factory=list)
    image: list[str] = field(default_factory=list)
