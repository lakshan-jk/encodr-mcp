"""Safe asynchronous ffmpeg/ffprobe process runner.

All commands are executed with an explicit argument list (never a shell string),
so filenames and user input cannot inject shell commands.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass

DEFAULT_TIMEOUT = 3600  # seconds


class FFmpegError(RuntimeError):
    """Raised when ffmpeg/ffprobe exits non-zero or is unavailable."""


@dataclass(slots=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def stderr_tail(self) -> str:
        return "\n".join(self.stderr.splitlines()[-25:])


def binary_path(name: str) -> str:
    """Locate ``ffmpeg``/``ffprobe`` on PATH or raise a clear error."""
    found = shutil.which(name)
    if not found:
        raise FFmpegError(
            f"'{name}' was not found on PATH. Install FFmpeg (e.g. `brew install ffmpeg`)."
        )
    return found


async def run(
    args: list[str],
    *,
    binary: str = "ffmpeg",
    timeout: float = DEFAULT_TIMEOUT,
) -> RunResult:
    """Run ``binary`` with ``args`` and capture output.

    Raises :class:`FFmpegError` on non-zero exit or timeout.
    """
    exe = binary_path(binary)
    proc = await asyncio.create_subprocess_exec(
        exe,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise FFmpegError(f"{binary} timed out after {timeout}s") from exc

    out = out_b.decode("utf-8", "replace")
    err = err_b.decode("utf-8", "replace")
    assert proc.returncode is not None
    if proc.returncode != 0:
        tail = "\n".join(err.splitlines()[-25:])
        raise FFmpegError(f"{binary} failed (exit {proc.returncode}):\n{tail}")
    return RunResult(proc.returncode, out, err)
