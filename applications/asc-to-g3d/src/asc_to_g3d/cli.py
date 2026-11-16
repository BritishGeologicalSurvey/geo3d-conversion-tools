"""Command line interface for converting ASC files to G3D.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer  # type: ignore
from rich.logging import RichHandler  # type: ignore

import asc_to_g3d.io
from asc_to_g3d import project
from asc_to_g3d.converter import convert_multiple_asc_to_g3d
from asc_to_g3d.g3d import G3DBoundsXYZ
from asc_to_g3d.io import ReadableSource, WritableTarget
from asc_to_g3d.job import Job


def setup_logging(verbose: bool):
    """Configures standard logging specifically for terminal output."""
    # Determine log level based on user flag
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure the global root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",  # RichHandler handles timestamps/levels cleanly
        datefmt="[%X]",  # Formats time as [HH:MM:SS]
        handlers=[
            RichHandler(
                rich_tracebacks=True,  # Prints beautiful error tracebacks
                show_path=verbose,  # Shows file/line number only in verbose mode
                markup=True,  # Allows you to use [bold red] tags in logs
            )
        ],
    )


# Initialize the Typer app
app = typer.Typer(
    name="asc_to_g3d", help="A CLI tool to process pairs of ASC grid files either individually or in batches."
)


@app.command()
def single(
    output_file: Annotated[Path, typer.Option("-o", "--output", help="Path to the generated output g3d file")],
    file_top: Annotated[Path | None, typer.Option("-top", "--file-top", help="Path to the 'top' input file")] = None,
    file_base: Annotated[
        Path | None, typer.Option("-base", "--file-base", help="Path to the 'base' input file")
    ] = None,
    file_thick: Annotated[
        Path | None, typer.Option("-thick", "--file-thick", help="Path to the 'thickness' input file")
    ] = None,
    strict: Annotated[bool, typer.Option("-s", "--strict", help="Strict mode")] = False,
    thickness_threshold: Annotated[float, typer.Option("-z", "--zero", help="Thickness zero threshold")] = 1e-5,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Verbose mode")] = False,
    layer_config: Annotated[
        Path | None, typer.Option("-c", "--layer-config", help="Path to an optional 'layer' CSV configuration file")
    ] = None,
) -> None:
    """Process a single, explicit pair of files."""

    setup_logging(verbose)

    # Count of inputs

    provided_files = {
        # i.e. if file_top exists it returns {"top": file_top}, and the ** unpacks a dictionary into another dictionary
        **({"top": file_top} if file_top is not None else {}),
        **({"base": file_base} if file_base is not None else {}),
        **({"thickness": file_thick} if file_thick is not None else {}),
    }

    provided_files_count = len(provided_files.keys())

    # O or 1 input file
    if provided_files_count < 2:
        typer.secho(
            f"Error: You must provide at least 2 input files. You provided {provided_files_count}: "
            f"({', '.join(provided_files.keys()) if provided_files_count else 'none'}).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    # 3+ input files
    elif provided_files_count > 2:
        typer.secho(
            f"ℹInformation: You provided more than 2 input files. You provided {provided_files_count}\nBut that's OK, processing can continue with: "  # noqa - line length
            f"({', '.join(provided_files.keys()) if provided_files_count else 'none'}).",
            fg=typer.colors.YELLOW,
            err=False,
        )

    typer.echo(f"Processing single mode using types: {', '.join(provided_files)}")
    for label, path in provided_files.items():
        typer.echo(f"Input {label}: {path}")
    typer.echo(f"Output: {output_file}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_json = output_file.parent / f"asc_to_g3d_project_{timestamp}.json"

    typer.echo(f"Project .json file will be written to: {project_json.absolute()}")

    job = Job(
        layer_name=output_file.stem,
        g3d_output=output_file,
        strict=strict,
        thickness_threshold=thickness_threshold,
        top=file_top,
        base=file_base,
        thickness=file_thick,
    )

    _process_jobs([job], project_json, layer_config, verbose)


@app.command()
def batch(
    directory: Annotated[
        Path,
        typer.Option(
            "-d", "--dir", help="Directory containing input files", exists=True, file_okay=False, dir_okay=True
        ),
    ],
    suffix_top: Annotated[str, typer.Option("--suffix-top", help="Optional suffix identifying 'top' files")] = "T",
    suffix_base: Annotated[str, typer.Option("--suffix-base", help="Optional suffix identifying 'base' files")] = "B",
    suffix_thick: Annotated[
        str, typer.Option("--suffix-thick", help="Optional suffix identifying 'thickness' files")
    ] = "TH",
    suffix_out: Annotated[str, typer.Option("--suffix-out", help="Optional suffix for output files")] = ".g3d",
    out_dir: Annotated[
        Path | None, typer.Option("-o", "--out-dir", help="Optional output directory. Defaults to source dir.")
    ] = None,
    strict: Annotated[bool, typer.Option("-s", "--strict", help="Strict mode")] = False,
    thickness_threshold: Annotated[float, typer.Option("-z", "--zero", help="Thickness zero threshold")] = 1e-5,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Verbose mode")] = False,
    layer_config: Annotated[
        Path | None, typer.Option("-c", "--layer-config", help="Path to an optional 'layer' CSV configuration file")
    ] = None,
) -> None:
    """Scan a directory for matching file pairs and process them all."""

    setup_logging(verbose)

    # Determine the target output directory
    target_out = out_dir if out_dir else directory
    target_out.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Scanning directory: {directory}")

    # Gather all unique base names across all three suffixes
    layer_names: dict[str, dict[str, Path]] = _get_layer_names(directory, suffix_top, suffix_base, suffix_thick)

    processing_jobs = []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_json = target_out / f"asc_to_g3d_project_{timestamp}.json"
    typer.echo(f"Project .json file will be written to: {project_json.absolute()}")

    # Loop over found layer names
    for layer_name, provided_files in layer_names.items():
        typer.echo(f"Layer: {layer_name}")

        g3d_output_file = target_out / f"{layer_name}{suffix_out}"
        labels = ", ".join(provided_files.keys())
        provided_files_count = len(provided_files.keys())

        # Loop through the inner dictionary
        for key, file_path in provided_files.items():
            # Indent with spaces for a clean, nested look
            typer.echo(f"   +- {key}: {file_path}")
            provided_files[key] = file_path

        if provided_files_count == 2:
            # 2 files
            typer.echo(f"Found 2 input files for '{layer_name}' using [{labels}] -> creating {g3d_output_file.name}")

            job = Job(
                layer_name=layer_name,
                g3d_output=g3d_output_file,
                strict=strict,
                thickness_threshold=thickness_threshold,
                top=provided_files.get("top"),
                base=provided_files.get("base"),
                thickness=provided_files.get("thickness"),
            )
            processing_jobs.append(job)

        elif provided_files_count > 2:
            # 3+ files
            typer.secho(
                f"Found more than 2 input files for '{layer_name}'. But that's OK, processing can continue with [{labels}] -> creating {g3d_output_file.name}",  # noqa - line length
                fg=typer.colors.YELLOW,
            )

            job = Job(
                layer_name=layer_name,
                g3d_output=g3d_output_file,
                strict=strict,
                thickness_threshold=thickness_threshold,
                top=provided_files.get("top"),
                base=provided_files.get("base"),
                thickness=provided_files.get("thickness"),
            )
            processing_jobs.append(job)
        elif provided_files_count < 2:
            # < 2 files
            typer.secho(
                f"Warning found only 1 input file for '{layer_name}' [{labels}] -> will not be able to create an output file!",  # noqa - line length
                fg=typer.colors.RED,
            )

    _process_jobs(processing_jobs, project_json, layer_config, verbose)


def _make_suffix_regex(suffix: str) -> str:
    """Make a regex that will match a case-insensitive suffix."""

    #  Convert each character into a [Cc] case-insensitive block,
    # checks in case the text contains numbers or special characters.
    body = "".join(f"[{char.upper()}{char.lower()}]" if char.isalpha() else re.escape(char) for char in suffix)

    # Combine with the prefix and the end-of-string anchor ($)
    return f"[-_]{body}$"


# Get files that share a layer names from all files within directory
def _get_layer_names(
    directory: Path, suffix_top: str, suffix_base: str, suffix_thick: str
) -> dict[str, dict[str, Path]]:
    """Identify all possible layer names based on the files within a directory that match the provided suffixes."""

    regexes = {
        "top": _make_suffix_regex(suffix_top),
        "base": _make_suffix_regex(suffix_base),
        "thickness": _make_suffix_regex(suffix_thick),
    }

    layer_names: defaultdict[str, dict[str, Path]] = defaultdict(dict[str, Path])

    for file in directory.iterdir():
        if file.is_file():
            stem = file.stem

            for key, regex in regexes.items():
                if re.search(regex, stem):
                    layer_name = re.sub(regex, "", stem)
                    layer_names[layer_name][key] = file

    typer.echo(f"Found {len(layer_names)} layer names")
    return layer_names


# Process jobs
def _process_jobs(
    processing_jobs: list[Job], project_json: WritableTarget, layer_config: ReadableSource | None, verbose: bool
):
    typer.echo(f"{len(processing_jobs)} jobs to process")
    typer.echo("Processing...")
    bounded_g3d_tuple: tuple[list[G3DBoundsXYZ], int] = convert_multiple_asc_to_g3d(processing_jobs, verbose)

    if bounded_g3d_tuple[1] > 0:
        typer.echo(f"Failed layers: {bounded_g3d_tuple[1]}")

    bounded_g3d_list: list[G3DBoundsXYZ] = bounded_g3d_tuple[0]

    project_json_str: str = project.make_project_json(bounded_g3d_list, layer_config, verbose)

    asc_to_g3d.io.write(project_json_str, project_json)
    typer.echo("JSON project has been written.")
    typer.echo("Copyright © UKRI (British Geological Survey) and the Polish Geological Institute 2026.")


#  This fallback triggers when no subcommands are provided
@app.callback(invoke_without_command=True)
def no_subcommand(ctx: typer.Context):
    """Called if no sub command is passed to the cli as it's first argument."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        typer.echo("Copyright © UKRI (British Geological Survey) and the Polish Geological Institute 2026.")
        raise typer.Exit()


# main
def main():
    """Main entry point function, for occasions when a function is required instead of 'if __name__ == "__main__"'."""
    try:
        app()
    finally:
        # This will ALWAYS run, even if Typer throws an error or exits early
        input("\nPress Enter to exit...")


# Run main code, take whatever result code it gives back (0 or 1),
# hand it to the terminal, and shut down the program immediately.
if __name__ == "__main__":
    sys.exit(main())
