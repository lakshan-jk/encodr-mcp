"""Path validation and optional sandboxing.

By default the server can read/write anywhere the OS user can. Set the
``ENCODR_MCP_ROOT`` environment variable to confine all input/output paths to a
single directory tree — useful when the server is exposed to an untrusted
agent.
"""

from __future__ import annotations

import os
from pathlib import Path


class PathError(ValueError):
    """Raised when a path is missing, invalid, or outside the allowed root."""


def _allowed_root() -> Path | None:
    root = os.environ.get("ENCODR_MCP_ROOT")
    return Path(root).expanduser().resolve() if root else None


def _enforce_root(path: Path) -> None:
    root = _allowed_root()
    if root is None:
        return
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PathError(
            f"Path {path} is outside the allowed root {root} (ENCODR_MCP_ROOT)."
        ) from exc


def resolve_input(path: str) -> Path:
    """Resolve an existing input file, enforcing the optional sandbox root."""
    p = Path(path).expanduser().resolve()
    _enforce_root(p)
    if not p.exists():
        raise PathError(f"Input file does not exist: {p}")
    if not p.is_file():
        raise PathError(f"Input path is not a file: {p}")
    return p


def resolve_output(path: str, *, overwrite: bool) -> Path:
    """Resolve an output file, creating parent dirs and honoring ``overwrite``."""
    p = Path(path).expanduser().resolve()
    _enforce_root(p)
    if p.exists() and not overwrite:
        raise PathError(f"Output already exists (set overwrite=true to replace): {p}")
    if p.is_dir():
        raise PathError(f"Output path is a directory: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
