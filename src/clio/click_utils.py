import signal
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import BinaryIO, TextIO

import click
from click import ClickException

from .__version__ import __version__
from .input import Source, TypeName, get_input
from .output import OutputDest, resolve_output_path, write_output

# Respect SIGPIPE so that `clio | head` quits silently instead of a Python traceback
_ = signal.signal(signal.SIGPIPE, signal.SIG_DFL)

__all__ = ("command_with_io",)

type DataType = str | bytes | Path | TextIO | BinaryIO


def command_with_io(func: Callable[..., DataType]) -> click.Command:
    """
    Decorate a function into a Click command with automatic I/O handling.

    Adds:
      - a `--version` flag (pulled from __version__.py)
      - a `--force` option to overwrite existing files
      - broad exception handling so any unexpected exception
        becomes a clean ClickException
    """

    @click.command()
    @click.version_option(version=__version__)
    @click.option(
        "--input-source",
        "input_source",
        type=click.Choice([s.value for s in Source], case_sensitive=False),
        default=Source.PIPE.value,
        show_default=True,
        help="Where to read input from.",
    )
    @click.option(
        "--input-name",
        "input_name",
        type=click.Path(exists=False, allow_dash=True),
        default="-",
        show_default=True,
        help="Name for input (env var, file path, or '-' for stdin).",
    )
    @click.option(
        "--input-type",
        "input_type",
        type=click.Choice([t.value for t in TypeName], case_sensitive=False),
        default=TypeName.STR.value,
        show_default=True,
        help="Which Python type to produce from the input.",
    )
    @click.option(
        "--output-dest",
        "output_dest",
        type=click.Choice([d.value for d in OutputDest], case_sensitive=False),
        default=OutputDest.PIPE.value,
        show_default=True,
        help="Where to write the command's result.",
    )
    @click.option(
        "--output-name",
        "output_name",
        type=click.Path(exists=False, allow_dash=True),
        default="-",
        show_default=True,
        help="Name for output (env var name or file path, or '-' for stdout).",
    )
    @click.option(
        "--force",
        is_flag=True,
        default=False,
        help="Overwrite existing output files when using file output.",
    )
    @wraps(func)
    def wrapper(
        input_source: str,
        input_name: str,
        input_type: str,
        output_dest: str,
        output_name: str,
        *,
        force: bool,
    ) -> None:
        def _wrap_error(err: Exception) -> None:
            raise ClickException(str(err)) from err

        try:
            # Parse enum values
            src = Source(input_source)
            typ = TypeName(input_type)
            dest = OutputDest(output_dest)

            # Read in the data
            data = get_input(src, name=input_name, as_type=typ)
            # Run the user's function
            result = func(data)

            # Validate return type
            if not isinstance(result, str | bytes | Path) and not hasattr(result, "read"):
                _wrap_error(TypeError(f"Unsupported return type: {type(result)}"))

            # Handle --force when writing to a file
            if dest is OutputDest.FILE and output_name not in {None, "-"}:
                path = resolve_output_path(output_name, force=force)
                output_name = str(path)

            # Write the output
            write_output(result, dest=dest, name=output_name)

        except ClickException:
            # Propagate expected CLI errors
            raise
        except Exception as err:  # noqa: BLE001
            # Wrap all other exceptions for a clean CLI error
            _wrap_error(err)

    return wrapper
