import atexit
import contextlib
import tempfile
from pathlib import Path
from typing import Literal


def persist_to_tempfile(
    data: str | bytes,
    *,
    mode: Literal["w", "wb"] = "w",
    suffix: str = "",
) -> Path:
    """Write data to a temp file and return its path."""
    ext = ".bin" if "b" in mode else ".txt"
    with tempfile.NamedTemporaryFile(
        delete=False,
        mode=mode,
        suffix=suffix or ext,
        encoding="utf-8" if mode == "w" else None,
    ) as f:
        _ = f.write(data)
        f.flush()
        temp_path = Path(f.name).resolve()

    def _cleanup(path: Path) -> None:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()

    _ = atexit.register(_cleanup, temp_path)
    return temp_path
