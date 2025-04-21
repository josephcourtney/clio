import io
import sys
from pathlib import Path

import pytest

from clio.input import get_input
from clio.output import resolve_output_path


def test_get_input_env_str(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "value123")
    assert get_input("env", name="TEST_VAR", as_type="str") == "value123"


def test_get_input_file_str(temp_text_file):
    assert get_input("file", name=temp_text_file, as_type="str") == "hello"


def test_get_input_pipe_str(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin"))
    assert get_input("pipe", as_type="str") == "from stdin"


def test_get_input_arg_str(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "first", "second"])
    assert get_input("arg", name="2", as_type="str") == "second"


def test_get_input_path(temp_text_file):
    p = get_input("file", name=temp_text_file, as_type="path")
    assert p.read_text() == "hello"


def test_invalid_input_type():
    with pytest.raises(ValueError, match="Unsupported type:"):
        get_input("file", name="whatever", as_type="xml")


def test_get_input_invalid_source():
    with pytest.raises(ValueError, match="Unsupported source:"):
        get_input("nonsense", as_type="str")


@pytest.mark.parametrize("source", ["arg", "env", "file", "signal"])
def test_get_input_missing_name(source):
    with pytest.raises(ValueError, match=f"Missing name for source '{source}'"):
        get_input(source, name=None, as_type="str")


def test_get_input_env_bytes(monkeypatch, tmp_path):
    # env var points at a file containing bytes
    f = tmp_path / "data.bin"
    f.write_bytes(b"bar")
    monkeypatch.setenv("FOO", str(f))
    result = get_input("env", name="FOO", as_type="bytes")
    assert isinstance(result, bytes)
    assert result == b"bar"


def test_get_input_as_textio(temp_text_file):
    with get_input("file", name=temp_text_file, as_type="textio") as stream:
        assert stream.read() == "hello"


def test_get_input_as_bufferedio(tmp_path):
    f = tmp_path / "binary.dat"
    f.write_bytes(b"abc")
    with get_input("file", name=str(f), as_type="bufferedio") as stream:
        assert stream.read() == b"abc"


def test_clipboard_as_path(monkeypatch):
    monkeypatch.setattr("clio.clipboard.pyperclip.paste", lambda: "clipboard content")
    p = get_input("clipboard", as_type="path")
    assert isinstance(p, Path)
    assert p.read_text() == "clipboard content"


def test_env_as_textio(monkeypatch, tmp_path):
    f = tmp_path / "my.txt"
    f.write_text("from env path")
    monkeypatch.setenv("MYFILE", str(f))
    with get_input("env", name="MYFILE", as_type="textio") as stream:
        assert stream.read() == "from env path"


def test_arg_as_bufferedio(monkeypatch, tmp_path):
    f = tmp_path / "bin.dat"
    f.write_bytes(b"\x00\x01")
    monkeypatch.setattr(sys, "argv", ["prog", str(f)])
    with get_input("arg", name="1", as_type="bufferedio") as stream:
        assert stream.read() == b"\x00\x01"


def test_env_as_path(monkeypatch, tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("env file")
    monkeypatch.setenv("MYFILE", str(f))
    p = get_input("env", name="MYFILE", as_type="path")
    assert p.read_text() == "env file"


def test_arg_as_textio(monkeypatch, tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("via arg path")
    monkeypatch.setattr(sys, "argv", ["prog", str(f)])
    with get_input("arg", name="1", as_type="textio") as stream:
        assert stream.read() == "via arg path"


def test_resolve_output_path(tmp_path):
    out = tmp_path / "out.txt"
    path = resolve_output_path(str(out))
    assert path == out.resolve()

    out.write_text("already exists")
    with pytest.raises(FileExistsError):
        resolve_output_path(str(out), force=False)
    assert resolve_output_path(str(out), force=True) == out.resolve()
