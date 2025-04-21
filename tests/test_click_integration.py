from click.testing import CliRunner

from clio.click_utils import command_with_io


@command_with_io
def cli(_data):
    return _data.upper()


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


# A “normal” command that just returns its input
@command_with_io
def echo(data):
    return data


@command_with_io
def bad_return(_data):
    # Return an unsupported type (int)
    return 123


def test_invalid_input_source():
    runner = CliRunner()
    result = runner.invoke(echo, ["--input-source", "bogus"], input="foo")
    assert result.exit_code == 2
    assert "Invalid value for '--input-source': 'bogus' is not one of" in result.output


def test_invalid_input_type():
    runner = CliRunner()
    result = runner.invoke(echo, ["--input-type", "xml"], input="foo")
    assert result.exit_code == 2
    assert "Invalid value for '--input-type': 'xml' is not one of" in result.output


def test_invalid_output_dest():
    runner = CliRunner()
    result = runner.invoke(echo, ["--output-dest", "database"], input="foo")
    assert result.exit_code == 2
    assert "Invalid value for '--output-dest': 'database' is not one of" in result.output


def test_unsupported_return_type():
    runner = CliRunner()
    result = runner.invoke(bad_return, [], input="ignored")
    assert result.exit_code != 0
    assert "Unsupported return type: <class 'int'>" in result.output
