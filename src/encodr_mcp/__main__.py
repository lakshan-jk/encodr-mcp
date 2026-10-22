"""Console entrypoint: `encodr-mcp` or `python -m encodr_mcp`."""

from __future__ import annotations

from .server import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
