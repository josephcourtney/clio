import io
import os
import sys
import tempfile
from pathlib import Path

import pytest

from clio.clipboard import read_clipboard
from clio.output import resolve_output_path, write_output


def test_write_output_env():
    write_output("ENV_VALUE", dest="env", name="MY_OUTPUT")
    assert os.environ["MY_OUTPUT"] == "ENV_VALUE"


def test_write_output_file(tmp_path):
    file_path = tmp_path / "out.txt"
    write_output("FILE_VALUE", dest="file", name=str(file_path))
    assert file_path.read_text() == "FILE_VALUE"


def test_write_output_pipe(monkeypatch):
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    write_output("PIPE_VALUE", dest="pipe")
    assert buffer.getvalue() == "PIPE_VALUE"


def test_missing_env_name():
    with pytest.raises(ValueError, match="Must provide `name` for env var output"):
        write_output("value", dest="env")


def test_missing_file_name():
    with pytest.raises(ValueError, match="Must provide `name` for file output"):
        write_output("value", dest="file")


def test_unsupported_dest():
    with pytest.raises(ValueError, match="Unsupported output destination:"):
        write_output("value", dest="database")


def test_write_output_from_path(tmp_path):
    input_path = tmp_path / "source.txt"
    input_path.write_text("write this")
    output_path = tmp_path / "dest.txt"
    write_output(input_path, dest="file", name=str(output_path))
    assert output_path.read_text() == "write this"


def test_write_output_from_stream(tmp_path):
    output_path = tmp_path / "stream.txt"
    stream = io.StringIO("from stream")
    write_output(stream, dest="file", name=str(output_path))
    assert output_path.read_text() == "from stream"


def test_output_from_textio(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("streamed")
    with f.open("r") as reader:
        write_output(reader, dest="file", name=str(tmp_path / "out.txt"))
    assert (tmp_path / "out.txt").read_text() == "streamed"


def test_output_from_binaryio(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"binary")
    with f.open("rb") as reader:
        write_output(reader, dest="pipe")


def test_output_from_path_to_clipboard(monkeypatch):
    # Use context manager for NamedTemporaryFile to satisfy SIM115
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name

    f = Path(tmp_name)
    f.write_text("from path")

    monkeypatch.setattr("clio.clipboard.pyperclip.copy", lambda x: setattr(sys.modules[__name__], "_clip", x))
    monkeypatch.setattr("clio.clipboard.pyperclip.paste", lambda: getattr(sys.modules[__name__], "_clip", ""))
    write_output(f, dest="clipboard")
    assert read_clipboard() == "from path"


def test_write_output_invalid_type():
    class NotSupported:
        pass

    with pytest.raises(TypeError, match="Unsupported data type for output"):
        write_output(NotSupported(), dest="pipe")


def test_resolve_output_path_missing_name():
    with pytest.raises(ValueError, match="Must provide a file name"):
        resolve_output_path(None)


def test_write_output_file_dash_writes_stdout(monkeypatch):
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    write_output("HELLO-DASH", dest="file", name="-")
    assert buffer.getvalue() == "HELLO-DASH"
