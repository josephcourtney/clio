import tempfile
from pathlib import Path

import pytest

MAX_OUTPUT_LINES = 32
MAX_TIME_PER_TEST = 2


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Limit captured output per test."""
    # Only modify output for the call phase (i.e. test execution)
    if report.when == "call" and report.failed:
        new_sections: list[tuple[str, str]] = []
        for title, content in report.sections:
            if title.startswith(("Captured stdout", "Captured stderr")):
                lines = content.splitlines()
                if len(lines) > MAX_OUTPUT_LINES:
                    truncated_section: str = "\n".join(lines[:MAX_OUTPUT_LINES] + ["... [output truncated]"])
                    new_sections.append((title, truncated_section))
                else:
                    new_sections.append((title, content))

            else:
                new_sections.append((title, content))
        report.sections = new_sections


@pytest.fixture
def temp_text_file():
    with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
        f.write("hello")
        f.flush()
        yield f.name
    Path(f.name).unlink()


def pytest_collection_modifyitems(config, items):  # noqa: ARG001 # call signature defined by pytest
    for test in items:
        test.add_marker(pytest.mark.timeout(MAX_TIME_PER_TEST))
