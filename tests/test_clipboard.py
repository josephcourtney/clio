import pytest

from clio.clipboard import read_clipboard, write_clipboard


def test_clipboard_not_installed(monkeypatch):
    monkeypatch.setattr("clio.clipboard.pyperclip", None)

    with pytest.raises(RuntimeError, match="pyperclip is not installed"):
        read_clipboard()

    with pytest.raises(RuntimeError, match="pyperclip is not installed"):
        write_clipboard("text")


def test_clipboard_mocked(mocker):
    mock_copy = mocker.patch("clio.clipboard.pyperclip.copy")
    mock_paste = mocker.patch("clio.clipboard.pyperclip.paste", return_value="mocked")

    write_clipboard("copied text")
    mock_copy.assert_called_once_with("copied text")

    result = read_clipboard()
    assert result == "mocked"
    mock_paste.assert_called_once()
