import pytest

from encodr_mcp.paths import PathError, resolve_input, resolve_output


def test_resolve_input_missing(tmp_path):
    with pytest.raises(PathError, match="does not exist"):
        resolve_input(str(tmp_path / "nope.mp4"))


def test_resolve_output_refuses_existing_without_overwrite(tmp_path):
    f = tmp_path / "out.mp4"
    f.write_bytes(b"x")
    with pytest.raises(PathError, match="already exists"):
        resolve_output(str(f), overwrite=False)


def test_resolve_output_creates_parent_dirs(tmp_path):
    target = tmp_path / "nested" / "deep" / "out.mp4"
    resolved = resolve_output(str(target), overwrite=True)
    assert resolved.parent.is_dir()


def test_sandbox_root_blocks_outside_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCODR_MCP_ROOT", str(tmp_path))
    with pytest.raises(PathError, match="outside the allowed root"):
        resolve_output("/etc/passwd", overwrite=True)
