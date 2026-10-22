# encodr-mcp

A high-quality, **local-first** [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes [FFmpeg](https://ffmpeg.org) transcoding to any MCP host (Claude Desktop, Claude Code, …).
Everything runs on your machine with open-source codecs — **no cloud, no upload, no quality
compromise**.

[![CI](https://github.com/lakshan-jk/encodr-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/lakshan-jk/encodr-mcp/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Why

LLM agents are great at *deciding* what to transcode but shouldn't be trusted to hand-write
`ffmpeg` incantations. `encodr-mcp` gives the model a small set of **safe, well-typed tools** with
**quality-first defaults** baked in — CRF-based encoding, `preset slow`, sensible pixel formats —
while still allowing full overrides.

## Quality policy

All presets use **constant-quality (CRF/VBR)** encoding, not fixed bitrate — the best
quality-per-byte. Defaults target visually-transparent output:

| Media | Codec options | Default |
|-------|---------------|---------|
| Video | `h264` (universal), `h265`, `av1` (best compression), `vp9` | H.264 CRF 18, `preset slow`, `yuv420p`, `+faststart` |
| Audio | `opus`, `aac`, `mp3`, `flac` (lossless), `wav` | Opus 160k VBR |
| Image | `webp`, `avif`, `jpeg`, `png` (lossless) | WebP q90 / AVIF CRF 23 |

Nothing is locked — every tool accepts `crf`, `preset`, `bitrate`, `quality`, scaling, and fps
overrides.

## Tools

| Tool | What it does |
|------|--------------|
| `probe_media` | Inspect format + streams (compact summary) |
| `list_codecs` | List supported codecs/formats and their defaults |
| `transcode_video` | Re-encode video (codec, CRF, scale, fps, audio) |
| `remux_video` | Change container with **no re-encode** (lossless, instant) |
| `transcode_audio` | Re-encode audio, optional EBU R128 loudness normalization |
| `extract_audio` | Pull the audio track out losslessly |
| `convert_image` | Convert/resize images |
| `thumbnail` | Grab a frame at a timestamp |
| `burn_subtitles` | Hardcode subtitles into video |
| `extract_stream` | Copy a single stream out by index |

## Requirements

- **FFmpeg** on your `PATH` (`ffmpeg` + `ffprobe`). macOS: `brew install ffmpeg`.
- **Python 3.11+**.

FFmpeg builds vary in which encoders/filters they ship. `encodr-mcp` **detects this at runtime**
and returns a clear error (e.g. *"webp requires the 'libwebp' encoder, which this FFmpeg build was
not compiled with"*) instead of failing cryptically. In particular, `convert_image` to WebP needs
`libwebp`, and `burn_subtitles` needs an FFmpeg built with `libass`. A full build (`brew install
ffmpeg`, or most Linux distro packages) includes both.

## Install

```bash
git clone https://github.com/lakshan-jk/encodr-mcp
cd encodr-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
encodr-mcp          # stdio transport
# or
python -m encodr_mcp
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ffmpeg": {
      "command": "/absolute/path/to/encodr-mcp/.venv/bin/encodr-mcp"
    }
  }
}
```

### Claude Code

```bash
claude mcp add ffmpeg -- /absolute/path/to/encodr-mcp/.venv/bin/encodr-mcp
```

## Security / sandboxing

By default the server can read and write anywhere your user can. To confine all input/output paths
to one directory tree, set:

```bash
export ENCODR_MCP_ROOT=/path/to/allowed/dir
```

Any path outside that root is rejected. Commands are always executed with an explicit argument list
(never a shell string), so filenames can't inject shell commands.

## Development

```bash
pytest            # unit tests + ffmpeg integration tests (auto-skipped if no ffmpeg)
ruff check .
mypy
```

## License

MIT © Lakshan Kumar JK
