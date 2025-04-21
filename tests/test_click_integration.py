from click.testing import CliRunner

from clio.click_utils import command_with_io


@command_with_io
def cli(data):
    return data.upper()


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
