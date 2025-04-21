import os
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, TextIO

from .clipboard import read_clipboard
from .signal import wait_for_signal
from .utils import persist_to_tempfile


class Source(StrEnum):
    ARG = "arg"
    ENV = "env"
    FILE = "file"
    PIPE = "pipe"
    CLIPBOARD = "clipboard"
    SIGNAL = "signal"


class TypeName(StrEnum):
    STR = "str"
    BYTES = "bytes"
    TEXTIO = "textio"
    BUFFEREDIO = "bufferedio"
    PATH = "path"


Reader = Callable[[Source, str | None], str | bytes | TextIO | BinaryIO | Path]


def _read_str(source: Source, name: str | None) -> str:  # noqa: C901
    if source in {Source.ARG, Source.ENV, Source.FILE, Source.SIGNAL} and name is None:
        msg = f"Missing name for source '{source}'"
        raise ValueError(msg)

    def _f_arg():
        if name is None:
            msg = "Missing name for signal source"
            raise ValueError(msg)
        return sys.argv[int(name)]

    def _f_env():
        if name is None:
            msg = "Missing name for signal source"
            raise ValueError(msg)
        return os.environ[name]

    def _f_file():
        if name is None:
            msg = "Missing name for signal source"
            raise ValueError(msg)
        return Path(name).read_text(encoding="utf-8")

    def _f_signal():
        if name is None:
            msg = "Missing name for signal source"
            raise ValueError(msg)
        return wait_for_signal(int(name))

    dispatch: dict[Source, Callable[[], str]] = {
        Source.ARG: _f_arg,
        Source.ENV: _f_env,
        Source.FILE: _f_file,
        Source.PIPE: sys.stdin.read,
        Source.CLIPBOARD: read_clipboard,
        Source.SIGNAL: _f_signal,
    }

    try:
        return dispatch[source]()
    except KeyError as e:
        msg = f"Unsupported source: {source}"
        raise ValueError(msg) from e


def _read_bytes(source: Source, name: str | None) -> bytes:
    if source in {Source.ARG, Source.ENV, Source.FILE, Source.SIGNAL} and name is None:
        msg = f"Missing name for source '{source}'"
        raise ValueError(msg)

    text = _read_str(source, name)
    path = Path(text)
    if path.is_file():
        return path.read_bytes()
    return text.encode("utf-8")


def _open_textio(source: Source, name: str | None) -> TextIO:
    if source == Source.PIPE:
        return sys.stdin
    if source == Source.FILE:
        if name is None:
            msg = "Missing name for textio file source"
            raise ValueError(msg)
        return Path(name).open("r", encoding="utf-8")
    if source in {Source.ENV, Source.ARG}:
        raw = _read_str(source, name)
        return Path(raw).open("r", encoding="utf-8")
    msg = f"Unsupported source for textio: {source}"
    raise ValueError(msg)


def _open_bufferedio(source: Source, name: str | None) -> BinaryIO:
    if source == Source.PIPE:
        return sys.stdin.buffer
    if source == Source.FILE:
        if name is None:
            msg = "Missing name for bufferedio file source"
            raise ValueError(msg)
        return Path(name).open("rb")
    if source in {Source.ENV, Source.ARG}:
        raw = _read_str(source, name)
        return Path(raw).open("rb")
    if source == Source.CLIPBOARD:
        raw = read_clipboard()
        tmp = persist_to_tempfile(raw.encode("utf-8"), mode="wb")
        return tmp.open("rb")
    if source == Source.SIGNAL:
        if name is None:
            msg = "Missing name for bufferedio signal source"
            raise ValueError(msg)
        raw = wait_for_signal(int(name))
        tmp = persist_to_tempfile(raw.encode("utf-8"), mode="wb")
        return tmp.open("rb")
    msg = f"Unsupported source for bufferedio: {source}"
    raise ValueError(msg)


def _read_path(source: Source, name: str | None) -> Path:
    if source in {Source.ARG, Source.ENV, Source.FILE, Source.SIGNAL} and name is None:
        msg = f"Missing name for source '{source}'"
        raise ValueError(msg)

    if source == Source.PIPE:
        content = sys.stdin.read()
        return persist_to_tempfile(content, mode="w")
    if source == Source.FILE:
        if name is None:
            msg = "Missing name for signal source"
            raise ValueError(msg)
        return Path(name).resolve()
    if source in {Source.ENV, Source.ARG}:
        raw = _read_str(source, name)
        return Path(raw).resolve()
    if source == Source.CLIPBOARD:
        raw = read_clipboard()
        return persist_to_tempfile(raw, mode="w")
    if source == Source.SIGNAL:
        msg = f"Unsupported source for path: {source}"
        raise ValueError(msg)
    msg = f"Unsupported source for path: {source}"
    raise ValueError(msg)


_READERS: dict[TypeName, Reader] = {
    TypeName.STR: _read_str,
    TypeName.BYTES: _read_bytes,
    TypeName.TEXTIO: _open_textio,
    TypeName.BUFFEREDIO: _open_bufferedio,
    TypeName.PATH: _read_path,
}


def get_input(
    source: Source,
    *,
    name: str | None = None,
    as_type: TypeName = TypeName.STR,
) -> str | bytes | TextIO | BinaryIO | Path:
    try:
        reader = _READERS[as_type]
    except KeyError as err:
        msg = f"Unsupported type: {as_type}"
        raise ValueError(msg) from err
    return reader(source, name)
