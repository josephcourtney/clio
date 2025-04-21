import io
import operator
import os
import signal
import sys
import threading
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from clio.click_utils import command_with_io
from clio.clipboard import read_clipboard, write_clipboard
from clio.input import get_input
from clio.output import write_output


@command_with_io
def cli(data):
    return data.upper()


class FakeStdin(io.TextIOBase):
    def __init__(self, binary_stream: io.BytesIO):
        self.buffer = binary_stream

    def read(self, *args, **kwargs):
        return self.buffer.read(*args, **kwargs).decode()


reverse = operator.itemgetter(slice(None, None, -1))


def test_env_str_to_file(tmp_path, monkeypatch):
    monkeypatch.setenv("INPUT", "hello")
    dest = tmp_path / "out.txt"

    text = get_input("env", name="INPUT", as_type="str")
    result = reverse(text)
    write_output(result, dest="file", name=str(dest))

    assert dest.read_text() == "olleh"


def test_env_bytes_to_pipe(monkeypatch, tmp_path, capsys):
    f = tmp_path / "in.bin"
    f.write_bytes(b"abc")
    monkeypatch.setenv("BIN", str(f))

    data = get_input("env", name="BIN", as_type="bytes")
    write_output(data[::-1], dest="pipe")

    assert capsys.readouterr().out == "cba"


def test_file_textio_to_clipboard(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello")

    with f.open():
        text = get_input("file", name=str(f), as_type="textio").read()
    write_output(reverse(text), dest="clipboard")

    assert read_clipboard() == "olleh"


def test_file_bufferedio_to_pipe(tmp_path, capsys):
    f = tmp_path / "bin.dat"
    f.write_bytes(b"abc")

    data = get_input("file", name=str(f), as_type="bufferedio").read()
    write_output(reverse(data), dest="pipe")

    assert capsys.readouterr().out == "cba"


def test_file_path_to_file(tmp_path):
    source = tmp_path / "a.txt"
    dest = tmp_path / "b.txt"
    source.write_text("hello")

    result = get_input("file", name=str(source), as_type="path")
    write_output(result, dest="file", name=str(dest))

    assert dest.read_text() == "hello"


def test_pipe_str_to_clipboard(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("banana"))
    text = get_input("pipe", as_type="str")
    write_output(reverse(text), dest="clipboard")

    assert read_clipboard() == "ananab"


def test_pipe_bytes_to_pipe(monkeypatch, capsys):
    byte_data = b"12345"
    buffer = io.BytesIO(byte_data)
    stdin = io.TextIOWrapper(buffer, encoding="utf-8")

    monkeypatch.setattr(sys, "stdin", stdin)

    result = get_input("pipe", as_type="bytes")
    write_output(reverse(result), dest="pipe")

    assert capsys.readouterr().out == "54321"


def test_arg_str_to_pipe(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "input", "hello"])
    text = get_input("arg", name="2", as_type="str")
    write_output(reverse(text), dest="pipe")

    assert capsys.readouterr().out == "olleh"


def test_signal_str_to_file(tmp_path):
    file_out = tmp_path / "signal.txt"

    def trigger():
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGUSR1)

    t = threading.Thread(target=trigger)
    t.start()

    text = get_input("signal", name=str(signal.SIGUSR1), as_type="str")
    write_output(f"got signal: {text}", dest="file", name=str(file_out))
    t.join()

    assert "SIGUSR1" in file_out.read_text()


def test_clipboard_to_pipe(capsys):
    write_clipboard("CLIP TEST")
    result = get_input("clipboard", as_type="str")
    write_output(reverse(result), dest="pipe")

    assert capsys.readouterr().out == "TSET PILC"


# ----------------------
# ✅ INPUT → PYTHON TYPE
# ----------------------

VALID_INPUT_COMBINATIONS = {
    "env": {"str", "bytes", "textio", "bufferedio", "path"},
    "arg": {"str", "bytes", "textio", "bufferedio", "path"},
    "file": {"str", "bytes", "textio", "bufferedio", "path"},
    "pipe": {"str", "bytes", "textio", "bufferedio", "path"},
    "clipboard": {"str", "bytes", "path"},
    "signal": {"str"},
}


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_input_matrix_env(py_type, tmp_path, monkeypatch):
    content = "matrix test ✓"
    content_bytes = content.encode()

    if py_type == "str":
        monkeypatch.setenv("MY_INPUT", content)
    else:
        f = tmp_path / "env_input.txt"
        f.write_text(content)
        monkeypatch.setenv("MY_INPUT", str(f))

    result = get_input("env", name="MY_INPUT", as_type=py_type)
    _assert_input_result(result, py_type, content, content_bytes)


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_input_matrix_arg(py_type, tmp_path, monkeypatch):
    content = "matrix test ✓"
    content_bytes = content.encode()

    if py_type == "str":
        monkeypatch.setattr(sys, "argv", ["prog", content])
    else:
        f = tmp_path / "arg_input.txt"
        f.write_text(content)
        monkeypatch.setattr(sys, "argv", ["prog", str(f)])

    result = get_input("arg", name="1", as_type=py_type)
    _assert_input_result(result, py_type, content, content_bytes)


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_input_matrix_file(py_type, tmp_path):
    content = "matrix test ✓"
    content_bytes = content.encode()

    f = tmp_path / "f.txt"
    f.write_text(content)
    result = get_input("file", name=str(f), as_type=py_type)
    _assert_input_result(result, py_type, content, content_bytes)


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_input_matrix_pipe(py_type, monkeypatch):
    content = "matrix test ✓"
    content_bytes = content.encode()

    if py_type == "bufferedio":
        stream = io.BytesIO(content_bytes)
        monkeypatch.setattr(sys, "stdin", FakeStdin(stream))
    else:
        monkeypatch.setattr(sys, "stdin", io.StringIO(content))

    result = get_input("pipe", as_type=py_type)
    _assert_input_result(result, py_type, content, content_bytes)


@pytest.mark.parametrize("py_type", ["str", "bytes", "path"])
def test_input_matrix_clipboard(py_type, monkeypatch):
    content = "matrix test ✓"
    monkeypatch.setattr("clio.clipboard.pyperclip.paste", lambda: content)
    result = get_input("clipboard", as_type=py_type)
    _assert_input_result(result, py_type, content, content.encode())


@pytest.mark.parametrize("py_type", ["str"])
def test_input_matrix_signal(py_type, monkeypatch):
    content = "matrix test ✓"
    monkeypatch.setattr("clio.input.wait_for_signal", lambda _: content)
    result = get_input("signal", name="12", as_type=py_type)
    _assert_input_result(result, py_type, content, content.encode())


def _assert_input_result(result, py_type, content, content_bytes):
    if py_type == "str":
        assert result == content
    elif py_type == "bytes":
        assert result == content_bytes
    elif py_type == "path":
        assert isinstance(result, Path)
        assert result.read_text() == content
    elif py_type == "textio":
        assert result.read() == content
        result.close()
    elif py_type == "bufferedio":
        assert result.read() == content_bytes
        result.close()


VALID_OUTPUT_COMBINATIONS = {"str", "bytes", "textio", "bufferedio", "path"}
OUTPUT_SINKS = {"env", "file", "pipe", "clipboard"}


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_output_matrix_env(py_type, tmp_path):
    content, data = _make_data_for_type(py_type, tmp_path)
    write_output(data, dest="env", name="MY_OUT")
    assert os.environ["MY_OUT"] == content
    _close_if_stream(data)


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_output_matrix_file(py_type, tmp_path):
    content, data = _make_data_for_type(py_type, tmp_path)
    out_path = tmp_path / "out.txt"
    write_output(data, dest="file", name=str(out_path))
    assert out_path.read_text(encoding="utf-8") == content
    _close_if_stream(data)


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_output_matrix_pipe(py_type, tmp_path, monkeypatch):
    content, data = _make_data_for_type(py_type, tmp_path)
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    write_output(data, dest="pipe")
    assert buffer.getvalue() == content
    _close_if_stream(data)


@pytest.mark.parametrize("py_type", ["str", "bytes", "textio", "bufferedio", "path"])
def test_output_matrix_clipboard(py_type, tmp_path, monkeypatch):
    content, data = _make_data_for_type(py_type, tmp_path)

    monkeypatch.setattr("clio.clipboard.pyperclip.copy", lambda x: setattr(sys.modules[__name__], "_clip", x))
    monkeypatch.setattr("clio.clipboard.pyperclip.paste", lambda: getattr(sys.modules[__name__], "_clip", ""))

    write_output(data, dest="clipboard")
    assert read_clipboard() == content
    _close_if_stream(data)


def _make_data_for_type(py_type, tmp_path):
    content = "streamed ✓"
    content_bytes = content.encode()

    match py_type:
        case "str":
            return content, content
        case "bytes":
            return content, content_bytes
        case "textio":
            file = tmp_path / "in.txt"
            file.write_text(content)
            return content, file.open("r")
        case "bufferedio":
            file = tmp_path / "in.bin"
            file.write_bytes(content_bytes)
            return content, file.open("rb")
        case "path":
            file = tmp_path / "in.txt"
            file.write_text(content)
            return content, file


def _close_if_stream(data):
    if hasattr(data, "close"):
        data.close()


def test_cli_pipe_to_pipe():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--input-source", "pipe", "--output-dest", "pipe"],
        input="hello",
    )
    assert result.exit_code == 0
    assert result.output == "HELLO"


def test_cli_file_to_file(tmp_path):
    infile = tmp_path / "in.txt"
    outfile = tmp_path / "out.txt"
    infile.write_text("world")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--input-source",
            "file",
            "--input-name",
            str(infile),
            "--output-dest",
            "file",
            "--output-name",
            str(outfile),
        ],
    )

    assert result.exit_code == 0
    assert outfile.read_text() == "WORLD"
