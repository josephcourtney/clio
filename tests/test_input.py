import io
import signal
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from clio.click_utils import command_with_io
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


def test_missing_name_for_textio_file_source():
    with pytest.raises(ValueError, match="Missing name for textio file source"):
        get_input("file", as_type="textio")


def test_unsupported_source_for_textio():
    with pytest.raises(ValueError, match="Unsupported source for textio: clipboard"):
        get_input("clipboard", as_type="textio")


def test_missing_name_for_bufferedio_file_source():
    with pytest.raises(ValueError, match="Missing name for bufferedio file source"):
        get_input("file", as_type="bufferedio")


def test_bufferedio_from_clipboard(monkeypatch):
    content = "clipboard data"
    monkeypatch.setattr("clio.clipboard.pyperclip.paste", lambda: content)
    stream = get_input("clipboard", as_type="bufferedio")
    assert stream.read() == content.encode("utf-8")
    stream.close()


def test_missing_name_for_bufferedio_signal_source():
    with pytest.raises(ValueError, match="Missing name for bufferedio signal source"):
        get_input("signal", as_type="bufferedio")


def test_missing_name_for_path_file_source():
    with pytest.raises(ValueError, match="Missing name for source 'file'"):
        get_input("file", as_type="path")


def test_missing_name_for_path_signal_source():
    with pytest.raises(ValueError, match="Missing name for source 'signal'"):
        get_input("signal", as_type="path")


def test_missing_name_for_path_env():
    with pytest.raises(ValueError, match="Missing name for source 'env'"):
        get_input("env", as_type="path")


@command_with_io
def broken_cli(_data):
    msg = "something went wrong"
    raise RuntimeError(msg)


def test_broken_cli_clean_message():
    runner = CliRunner()
    # use pipe→pipe so no file I/O
    result = runner.invoke(
        broken_cli,
        ["--input-source", "pipe", "--output-dest", "pipe"],
        input="foo",
    )
    assert result.exit_code != 0
    # should not show a Python traceback, just our message
    assert "Error: something went wrong" in result.output


@command_with_io
def echo_cli(data):
    return data


def test_overwrite_without_force(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text("old")
    runner = CliRunner()
    result = runner.invoke(
        echo_cli,
        [
            "--input-source",
            "pipe",
            "--output-dest",
            "file",
            "--output-name",
            str(out),
        ],
        input="new",
    )
    assert result.exit_code != 0
    assert "Output file exists" in result.output


def test_overwrite_with_force(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text("old")
    runner = CliRunner()
    result = runner.invoke(
        echo_cli,
        [
            "--input-source",
            "pipe",
            "--output-dest",
            "file",
            "--output-name",
            str(out),
            "--force",
        ],
        input="new",
    )
    assert result.exit_code == 0
    assert out.read_text() == "new"


def test_pipe_to_path(monkeypatch):
    # simulate stdin
    monkeypatch.setattr(sys, "stdin", io.StringIO("from-stdin"))
    p = get_input("pipe", as_type="path")
    assert isinstance(p, Path)
    assert p.read_text() == "from-stdin"
    # cleanup the tempfile
    p.unlink()


# Optionally, also test that SIGNAL→path is unsupported:
def test_signal_path_unsupported():
    # signal→path is not supported
    with pytest.raises(ValueError, match="Unsupported source for path: signal"):
        get_input("signal", name=str(signal.SIGUSR1), as_type="path")


def test_signal_bufferedio(monkeypatch):
    # Make wait_for_signal return a known string
    monkeypatch.setattr("clio.input.wait_for_signal", lambda _: "SIGTEST")
    # Should return a BinaryIO with that content
    stream = get_input("signal", name=str(signal.SIGUSR1), as_type="bufferedio")
    data = stream.read()
    stream.close()
    assert data == b"SIGTEST"


def test_signal_textio_unsupported(monkeypatch):
    monkeypatch.setattr("clio.input.wait_for_signal", lambda _: "ignored")
    with pytest.raises(ValueError, match="Unsupported source for textio: signal"):
        get_input("signal", name=str(signal.SIGUSR1), as_type="textio")


def test_signal_bytes(monkeypatch):
    monkeypatch.setattr("clio.input.wait_for_signal", lambda _: "HELLO")
    data = get_input("signal", name=str(signal.SIGUSR2), as_type="bytes")
    assert data == b"HELLO"


@pytest.mark.parametrize(
    ("as_type", "error_msg", "kwargs"),
    [
        ("bytes", "Unsupported source:", {}),
        ("textio", "Unsupported source for textio:", {"name": "dummy"}),
        ("bufferedio", "Unsupported source for bufferedio:", {"name": "dummy"}),
        ("path", "Unsupported source for path:", {"name": "dummy"}),
    ],
)
def test_invalid_source_all_types(as_type, error_msg, kwargs):
    # use `match=` to pin down the expected error text
    with pytest.raises(ValueError, match=error_msg):
        get_input("nonsense", as_type=as_type, **kwargs)


@pytest.mark.parametrize("source", ["arg", "env", "file", "signal"])
def test_missing_name_bytes(source):
    """Missing name errors for bytes type."""
    with pytest.raises(ValueError, match=f"Missing name for source '{source}'"):
        get_input(source, as_type="bytes")


@pytest.mark.parametrize("source", ["arg", "env", "file", "signal"])
def test__read_str(source):
    """Missing name errors for textio, bufferedio, and path when source is arg or env."""
    with pytest.raises(ValueError, match=f"Missing name for source '{source}'"):
        get_input(source, name=None)
