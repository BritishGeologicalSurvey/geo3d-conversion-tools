"""Conversion functions for converting ASC files to G3D files.
(also generates JSON snippets for Geo3D project.json)
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import logging
from typing import Any, cast

import numpy as np
import pandas as pd

import asc_to_g3d.io
from asc_to_g3d.asc import AscData, AscFootprint
from asc_to_g3d.g3d import G3D, G3DBoundsXY, G3DBoundsXYZ
from asc_to_g3d.job import Job
from asc_to_g3d.types import require_not_none as rnn

logger = logging.getLogger(__name__)


def convert_multiple_asc_to_g3d(jobs: list[Job], verbose: bool = False) -> tuple[list[G3DBoundsXYZ], int]:
    """Each "job" represents a set of ASC files that are to be converted to a G3D file.

    Args:
        jobs: list[Job] the jobs to process.
        verbose: bool, if true stack trace for errors will be logged.

    Returns:
         tuple[list[G3DBoundsXYZ], int], the bounds of G3D files created, the int is the number of failures 0 - if none
    """
    bounded_g3d_list: list[G3DBoundsXYZ] = []

    failures = 0

    for job in jobs:
        try:
            # convert the data to g3d
            bounded_g3d: G3DBoundsXYZ = convert_asc_to_g3d(job)
            bounded_g3d_list.append(bounded_g3d)

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Unexpected processing error {error_type} occurred: {e}", exc_info=verbose)
            failures = failures + 1

    return bounded_g3d_list, failures


def convert_asc_to_g3d(job: Job) -> G3DBoundsXYZ:
    """Process a "job" to convert set of ASC files to a G3D file.

    Args:
        job: Job the job to process.

    Returns:
        bounded G3D: G3DBoundsXYZ

    Raises:
        ValueError: Invalid or inconsistent data within the file.
        IOError: An error occurred accessing the file.
    """
    logger.info(f"Processing layer: {job.layer_name}")

    # if we have top and base: use those
    # if we have top and thickness: use top and (top minus thickness to get base)
    # if we have base and thickness: use top and (base plus thickness to get top)

    logger.debug(f"  top = {job.top}")
    logger.debug(f"  base = {job.base}")
    logger.debug(f"  thickness = {job.thickness}")
    logger.debug(f"  g3d output = {job.g3d_output}")
    logger.debug(f"  strict = {job.strict}")
    logger.debug(f"  thickness threshold = {job.thickness_threshold}")

    # always, even if just using the defaults
    strict = _is_true(job.strict)
    thickness_threshold = _to_float(job.thickness_threshold, default=1e-5)

    if job.has_top() and job.has_base():
        logger.debug("Using Top and Base surface data.")
        # read top and base
        top_asc: AscData = AscData.read_asc(rnn(job.top))  # noqa - checked for None
        base_asc: AscData = AscData.read_asc(rnn(job.base))  # noqa - checked for None
        # compare headers
        check_same_footprint(base_asc, top_asc)
        footprint: AscFootprint = top_asc.footprint
        # extract DataFrames
        top_data: pd.DataFrame = top_asc.data
        base_data: pd.DataFrame = base_asc.data
        # calc base
        thickness_data: pd.DataFrame = top_asc.data - base_asc.data
        # counts
        row_count: int = top_asc.nrows
        col_count: int = top_asc.ncols

    elif job.has_top() and job.has_thickness():
        logger.debug("Using Top and Thickness surface data (calculating Base: Top - Thickness).")
        top_path = job.top
        thickness_path = job.thickness
        # read top and thickness
        top_asc: AscData = AscData.read_asc(rnn(top_path))  # noqa - checked for None
        thickness_asc: AscData = AscData.read_asc(rnn(thickness_path))  # noqa - checked for None
        # compare headers
        check_same_footprint(top_asc, thickness_asc)
        footprint: AscFootprint = top_asc.footprint
        # extract DataFrames
        top_data: pd.DataFrame = top_asc.data
        thickness_data: pd.DataFrame = thickness_asc.data
        # calc base
        base_data: pd.DataFrame = top_asc.data - thickness_asc.data
        # counts
        row_count: int = top_asc.nrows
        col_count: int = top_asc.ncols

    elif job.has_base() and job.has_thickness():
        logger.debug("Using Base and Thickness surface data (calculating Top: Base + Thickness).")
        base_path = job.base
        thickness_path = job.thickness
        # read base and thickness
        base_asc: AscData = AscData.read_asc(rnn(base_path))  # noqa - checked for None
        thickness_asc: AscData = AscData.read_asc(rnn(thickness_path))  # noqa - checked for None
        # compare headers
        check_same_footprint(base_asc, thickness_asc)
        footprint: AscFootprint = base_asc.footprint
        # extract DataFrames
        base_data: pd.DataFrame = base_asc.data
        thickness_data: pd.DataFrame = thickness_asc.data
        # calc top
        top_data: pd.DataFrame = base_asc.data + thickness_asc.data
        # counts
        row_count: int = base_asc.nrows
        col_count: int = base_asc.ncols

    else:
        raise ValueError(
            "Insufficient data provided. Must have at least (top & base), (top & thickness), or (base & thickness)."
        )

    # g3d
    g3d_data: G3D = process_data(
        top_data,
        base_data,
        thickness_data,
        row_count,
        col_count,
        thickness_threshold,
        strict,
    )

    g3d_bounds = G3DBoundsXY(
        ncols=footprint.ncols,
        nrows=footprint.nrows,
        cellsize=footprint.cellsize,
        origin_x=footprint.origin_x,
        origin_y=footprint.origin_y,
        min_x=footprint.origin_x - (footprint.cellsize / 2.0),
        max_x=(footprint.origin_x - (footprint.cellsize / 2.0)) + (footprint.ncols * footprint.cellsize),
        min_y=footprint.origin_y - (footprint.cellsize / 2.0),
        max_y=(footprint.origin_y - (footprint.cellsize / 2.0)) + (footprint.nrows * footprint.cellsize),
    )

    # write the g3d file
    asc_to_g3d.io.write(g3d_data.file_content, rnn(job.g3d_output))
    logger.info(f"G3D has been written for layer: {job.layer_name}")

    return G3DBoundsXYZ(
        layer_name=rnn(job.layer_name), bounds_xy=g3d_bounds, min_z=g3d_data.min_z, max_z=g3d_data.max_z
    )


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)

    # fmt: off
    # ruff tries to remove required parentheses around multiple exceptions.
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return default
    # fmt: on


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in {"true", "t"}


# Ensure both datasets align spatially before computation
def _check_nan_correspondence(a_data, b_data, c_data, strict=True):
    # Check if corresponding elements are both NaN or both have float values
    all_nan = np.isnan(a_data) & np.isnan(b_data) & np.isnan(c_data)

    # Check if ALL are finite using &
    all_finite = np.isfinite(a_data) & np.isfinite(b_data) & np.isfinite(c_data)

    # Combine them using |
    all_nan_or_all_finite = all_nan | all_finite

    array = np.asarray(all_nan_or_all_finite)

    # Check if all values in both_nan_or_float are True
    all_true: bool = bool(array.all())
    false_count: int = (~array).sum()

    if all_true:
        logger.debug("All corresponding elements are either both NaN or both finite float values.")
    elif strict:
        raise ValueError(f"{false_count} corresponding elements differ (one is NaN and the other is a finite float)!")
    else:
        logger.warning(f"{false_count} corresponding elements differ (one is NaN and the other is a finite float)!")


def check_same_footprint(a_asc: AscData, b_asc: AscData):
    """Raised an error if the two arguments have a different AscFootprint.

    Args:
        a_asc: AscData
        b_asc: AscData
    Raises:
        ValueError if footprints not the same.
    """
    if a_asc.footprint != b_asc.footprint:
        raise ValueError("The footprint of the ASC data files do not match!")


def process_data(
    top_data: pd.DataFrame,
    base_data: pd.DataFrame,
    thickness_data: pd.DataFrame,
    row_count: int,
    col_count: int,
    thickness_threshold: float = 1e-5,
    strict: bool = False,
) -> G3D:
    """Processes ASC data to generate G3D data.

    Args:
        top_data: pd.DataFrame, top surface data
        base_data: pd.DataFrame, base surface data
        thickness_data: pd.DataFrame, thickness data (difference between top and base)
        row_count: int, the row count of the data frames
        col_count: int, the column count of the data frames
        thickness_threshold: float = 1e-5, the thickness below which cell values are removed
        strict: bool = False, when True comparing NaN values in the data frames raises a
            ValueError if there isn't a corresponding NaN in all data frames

    Returns:
        G3D, representation of a G3D file

    Raises:
        ValueError: Invalid or inconsistent data within the data.
    """

    # Compare nans
    _check_nan_correspondence(top_data, base_data, thickness_data, strict)

    # To get this far all data must have had the same dimensions
    logger.debug(f"Dimensions of original data rows: {row_count}, cols: {col_count}")

    # Check for negative thicknesses
    negative_thickness_count = (thickness_data < 0).to_numpy().sum()
    if negative_thickness_count > 0:
        logger.warning(
            f"The thickness data contains {negative_thickness_count} negative values, this will be filtered out!"
        )

    # DataFrame of stacked values
    stacked: pd.DataFrame = pd.DataFrame(
        {"top": top_data.stack(), "base": base_data.stack(), "thickness": thickness_data.stack()}
    )

    # Rename axes and add corrected y by
    stacked: pd.DataFrame = stacked.rename_axis(["inv-y", "x"]).reset_index()
    stacked["y"] = row_count - stacked["inv-y"] - 1

    # Round before filtering because we will want to drop anywhere thickness values
    # have rounded to below thickness_threshold
    rounded: pd.DataFrame = stacked.round({"top": 2, "base": 2, "thickness": 2})

    # Drop row with any nans
    filtered: pd.DataFrame = rounded.dropna(subset=["top", "base", "thickness"])

    # Drop rows with thickness < thickness_threshold (i.e. retain >= thickness_threshold)
    # The cast() is there to keep type checker happy
    filtered: pd.DataFrame = cast(pd.DataFrame, filtered[filtered["thickness"] >= abs(thickness_threshold)])

    logger.debug(
        f"The filtered data has {len(filtered)} entries after removing entries with NaN values or thickness below the threshold ({abs(thickness_threshold)})"  # noqa - line length
    )

    # Create a generator that formats each row
    formatted_rows = (
        f"{x}, {y}, {top:.2f}, {base:.2f}"
        for x, y, top, base in filtered[["x", "y", "top", "base"]].itertuples(index=False)
    )

    absolute_min_z = filtered[["top", "base"]].min().min()
    absolute_max_z = filtered[["top", "base"]].max().max()

    # Join all chunks with a comma-space and wrap the entire stream in brackets
    file_content = f"[{', '.join(formatted_rows)}]"

    return G3D(file_content=file_content, min_z=absolute_min_z, max_z=absolute_max_z)
