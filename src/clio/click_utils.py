import signal
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import BinaryIO, TextIO

import click
from click import ClickException

from .input import Source, TypeName, get_input
from .output import OutputDest, write_output

# Respect SIGPIPE so 'clio … | head' quits silently instead of a Python traceback
_ = signal.signal(signal.SIGPIPE, signal.SIG_DFL)


__all__ = ("command_with_io",)


def command_with_io(
    func: Callable[[str | bytes | Path | TextIO | BinaryIO], str | bytes | Path | TextIO | BinaryIO],
) -> click.Command:
    """Decorate a function to make it into an enhanced Click command.

    Turn a single-argument function into a Click command
    that reads from one of Source, passes the deserialized object in,
    and writes the function's return value to one of OutputDest.
    """

    @click.command()
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
        help="Name for input (e.g. env var, file path, or '-' for stdin).",
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
    @wraps(func)
    def wrapper(
        input_source: Source, input_name: str, input_type: TypeName, output_dest: OutputDest, output_name: str
    ) -> None:
        # Convert strings back into your enums, with clean error messages.
        try:
            src = Source(input_source)
        except ValueError as e:
            msg = f"Invalid input source: {input_source}"
            raise ClickException(msg) from e

        try:
            typ = TypeName(input_type)
        except ValueError as e:
            msg = f"Invalid input type: {input_type}"
            raise ClickException(msg) from e

        try:
            dest = OutputDest(output_dest)
        except ValueError as e:
            msg = f"Invalid output destination: {output_dest}"
            raise ClickException(msg) from e

        # Read in the data
        try:
            data = get_input(src, name=input_name, as_type=typ)
        except Exception as e:
            raise ClickException(str(e)) from e

        # Call the user's function
        result = func(data)

        # Validate the return type
        if not isinstance(result, (str | bytes | Path)) and not hasattr(result, "read"):
            msg = f"Unsupported return type: {type(result)}"
            raise ClickException(msg)

        # Write it out
        try:
            write_output(result, dest=dest, name=output_name)
        except Exception as e:
            raise ClickException(str(e)) from e

    return wrapper
