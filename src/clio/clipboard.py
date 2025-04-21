try:
    import pyperclip
except ImportError:
    pyperclip = None


def read_clipboard() -> str:
    if pyperclip is None:
        msg = "pyperclip is not installed"
        raise RuntimeError(msg)
    return pyperclip.paste()


def write_clipboard(data: str) -> None:
    if pyperclip is None:
        msg = "pyperclip is not installed"
        raise RuntimeError(msg)
    pyperclip.copy(data)
