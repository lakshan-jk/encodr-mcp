"""True end-to-end test: spawn the real server process and drive it over the
stdio MCP transport exactly as Claude Desktop / Claude Code would."""

from __future__ import annotations

import sys

import pytest

from conftest import make_video, requires_ffmpeg, tool_payload

pytestmark = requires_ffmpeg

mcp_client = pytest.importorskip("mcp.client.stdio")
from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402

SERVER = StdioServerParameters(command=sys.executable, args=["-m", "encodr_mcp"])


async def test_stdio_handshake_lists_all_tools():
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        names = {t.name for t in tools.tools}
        assert names == {
            "probe_media",
            "list_codecs",
            "transcode_video",
            "remux_video",
            "transcode_audio",
            "extract_audio",
            "convert_image",
            "thumbnail",
            "burn_subtitles",
            "extract_stream",
        }


async def test_stdio_probe_and_transcode(tmp_path):
    src = await make_video(tmp_path / "e2e.mp4", seconds=1, width=320, height=240)
    dst = tmp_path / "e2e_out.mp4"
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        probed = await session.call_tool("probe_media", {"path": str(src)})
        assert not probed.is_error
        assert tool_payload(probed)["video"][0]["width"] == 320

        out = await session.call_tool(
            "transcode_video",
            {
                "input": str(src),
                "output": str(dst),
                "video_codec": "h264",
                "crf": 30,
                "overwrite": True,
            },
        )
        assert not out.is_error
        assert dst.exists()


async def test_stdio_tool_schemas_are_published():
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = {t.name: t for t in (await session.list_tools()).tools}
        props = tools["transcode_video"].input_schema["properties"]
        assert "input" in props and "output" in props and "video_codec" in props


async def test_stdio_errors_surface_as_is_error_with_message(tmp_path):
    src = await make_video(tmp_path / "e.mp4", seconds=1, width=160, height=120)
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        # Missing input -> is_error with the helpful message preserved.
        missing = await session.call_tool("probe_media", {"path": "/no/such/file.mp4"})
        assert missing.is_error
        assert "does not exist" in missing.content[0].text

        # Bad codec -> is_error listing the valid choices.
        bad = await session.call_tool(
            "transcode_video",
            {
                "input": str(src),
                "output": str(tmp_path / "o.mp4"),
                "video_codec": "nope",
                "overwrite": True,
            },
        )
        assert bad.is_error
        assert "Unknown video codec" in bad.content[0].text
