"""© UKRI (British Geological Survey) and the Polish Geological Institute 2026."""

import io
from pathlib import Path
from typing import TextIO, cast

type ReadableSource = str | Path | TextIO
type WritableTarget = str | Path | TextIO


def source_to_stream(source: ReadableSource) -> TextIO:
    """Takes a ReadableSource and returns it as typing.TextIO.

        Remember to use the return value with "with ..."

    Args:
        source: ReadableSource

    Returns:
        typing.TextIO

    Raises:
        TypeError if source is not of a supported type
        FileNotFoundError if it's a Path that doesn't represent and file
        IOError: if an error occurred accessing the file.
    """

    source_stream: TextIO | None = None

    # Case 1: It's a file path
    if isinstance(source, Path):
        if not (source.exists() and source.is_file()):
            raise FileNotFoundError(f"The specified file was not found: '{source}'")

        source_stream = source.open(mode="r", encoding="utf-8")

    # Case 2: It's a raw data string
    elif isinstance(source, str):
        try:
            source_path = Path(source)

            # Case 2a: It's a raw file path string
            if source_path.exists() and source_path.is_file():
                source_stream = source_path.open(mode="r", encoding="utf-8")

            elif source_path.exists() and not source_path.is_file():
                raise FileNotFoundError(f"The specified file was not found: '{source}'")
            else:
                # Case 2b: It's a raw data string
                source_stream = io.StringIO(source)

        except OSError:
            # If the string contains characters illegal for OS paths,
            # treat it purely as raw data text.
            source_stream = io.StringIO(source)

    # Case 3: It's already an open stream, includes typing.TextIO
    elif isinstance(source, io.TextIOBase):
        source_stream = source

    # If source_stream not assigned
    if source_stream is None:
        raise TypeError("Unsupported source type")

    return source_stream


def target_to_stream(
    target: WritableTarget,
    as_file: bool | None = None,
) -> TextIO:
    """Takes a WritableSource and returns it as typing.TextIO for writing.

    Remember to use the return value with "with ..." to ensure files flush
    and save to disk correctly.

    Args:
        target: WritableSource
        as_file: Force interpretation as a file (True) or raw text string (False).  Leaves it to auto-detection if None.

    Returns:
        typing.TextIO

    Raises:
        TypeError if target is not of a supported type
        FileNotFoundError if the path's parent directory does not exist
        IOError: if an error occurred accessing or creating the file.
    """
    target_stream: TextIO | None = None

    # Case 1: It's a Path object
    if isinstance(target, Path):
        # We check the .parent directory because the file itself might not exist yet
        if not target.parent.exists():
            raise FileNotFoundError(f"The directory does not exist: '{target.parent}'")

        target_stream = target.open(mode="w", encoding="utf-8")

    # Case 2: It's a string (Path string OR initial buffer string)
    elif isinstance(target, str):
        is_path = as_file if as_file is not None else _is_likely_file_path(target)

        # Case 2a: It's a valid file path string (its directory directory exists)
        if is_path:
            target_path = Path(target)
            if not target_path.parent.exists():
                raise FileNotFoundError(f"The directory does not exist for path: '{target}'")
            target_stream = target_path.open(mode="w", encoding="utf-8")
        else:
            # Case 2b: It's raw text data or a buffer name, give them a StringIO stream
            # We seed it with the string so they can append, or start fresh
            target_stream = io.StringIO(target)

    # Case 3: It's already an open stream, includes typing.TextIO
    elif isinstance(target, io.TextIOBase):
        target_stream = cast(TextIO, target)

    # If target_stream not assigned
    if target_stream is None:
        raise TypeError("Unsupported target type")

    return target_stream


def _is_likely_file_path(target: str) -> bool:
    """Helper to determine if a string structurally looks like a path."""
    if "\n" in target:
        return False

    # If it explicitly uses path slashes
    if "/" in target or "\\" in target:
        return True

    return False


def write(data: str, target: WritableTarget) -> None:
    """Write data str to a WritableTarget.

    Args:
        data: str, data as a string
        target: WritableTarget where the data is written

    Raises:
        TypeError if target is not of a supported type
        IOError: An error occurred
    """

    with target_to_stream(target) as target_stream:
        target_stream.write(data)


def read(source: ReadableSource) -> str:
    """Read string from a ReadableSource.

    Args:
        source: ReadableSource where the data is read from

    Returns:
        str

    Raises:
        TypeError if source is not of a supported type
        IOError: An error occurred
    """

    with source_to_stream(source) as source_stream:
        return source_stream.read()


def read_lines(source: ReadableSource) -> list[str]:
    """Read string lines from a ReadableSource.

    Args:
        source: ReadableSource where the data is read from

    Returns:
        list[str]

    Raises:
        TypeError if source is not of a supported type
        IOError: An error occurred
    """

    with source_to_stream(source) as source_stream:
        return source_stream.readlines()


def get_filename(source: ReadableSource) -> str | None:
    """Extracts the filename from a file path or an opened file stream.

    This function accepts strings, pathlib.Path objects, or open file-like
    objects (TextIO). If an opened file stream is provided, it attempts to
    read its `.name` attribute. If the stream is in-memory (e.g., io.StringIO)
    and lacks a name, it returns None.

    Args:
        source (ReadableSource): A string representing a file path, a
            pathlib.Path object, or an opened file object (TextIO).

    Returns:
        str | None: The extracted filename (e.g., 'data.txt'), or None if
        the source is a stream without a valid filename.
    """
    # Using isinstance allows Pylance to strictly narrow the type to 'str | Path'
    if isinstance(source, (str, Path)):
        return Path(source).name

    # By this point, Pylance knows 'source' MUST be a TextIO stream
    name = getattr(source, "name", None)
    return Path(name).stem if name is not None else None
