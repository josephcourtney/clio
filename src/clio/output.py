import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, TextIO

from .clipboard import write_clipboard


class OutputDest(StrEnum):
    ENV = "env"
    FILE = "file"
    PIPE = "pipe"
    CLIPBOARD = "clipboard"


def extract_data(data: str | bytes | Path | TextIO | BinaryIO, encoding: str = "utf-8") -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, bytes):
        return data.decode(encoding)
    if isinstance(data, Path):
        return data.read_text(encoding=encoding)
    if hasattr(data, "read"):
        raw = data.read()
        return raw.decode(encoding) if isinstance(raw, bytes) else str(raw)
    msg = f"Unsupported data type for output: {type(data)}"
    raise TypeError(msg)


def _require_name(name: str | None, dest: str) -> str:
    if not name:
        msg = f"Must provide `name` for {dest} output"
        raise ValueError(msg)
    return name


def write_output(
    data: str | bytes | Path | TextIO | BinaryIO,
    *,
    dest: OutputDest,
    name: str | None = None,
    encoding: str = "utf-8",
) -> None:
    data_str = extract_data(data, encoding)

    match dest:
        case OutputDest.ENV:
            os.environ[_require_name(name, "env var")] = data_str
        case OutputDest.FILE:
            path = _require_name(name, "file")
            if path == "-":
                _ = sys.stdout.write(data_str)
            else:
                _ = Path(path).write_text(data_str, encoding=encoding)
        case OutputDest.PIPE:
            _ = sys.stdout.write(data_str)
        case OutputDest.CLIPBOARD:
            write_clipboard(data_str)
        case _:  # pyright:ignore[reportUnnecessaryComparison]
            msg = f"Unsupported output destination: {dest}"  # pyright:ignore[reportUnreachable]
            raise ValueError(msg)


def resolve_output_path(name: str | None, *, force: bool = False) -> Path:
    if not name:
        msg = "Must provide a file name"
        raise ValueError(msg)
    path = Path(name).resolve()
    if path.exists() and not force:
        msg = f"Output file exists: {path}. Use --force to overwrite."
        raise FileExistsError(msg)
    return path
