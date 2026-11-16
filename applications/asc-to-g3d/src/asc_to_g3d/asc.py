"""Module for loading and representing ASC files (ascii grid data from GIS).
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

import asc_to_g3d.io
from asc_to_g3d.types import require_not_none as rnn

logger = logging.getLogger(__name__)


class AscLowerLeft(Enum):
    """Enum of the different header options that represent the lower left cell position."""

    CENTERS = "centers"
    CORNERS = "corners"
    INVALID = "invalid"


@dataclass(slots=True, frozen=True)
class AscFootprint:
    """A data class representing the footprint of an ASC file's grid."""

    ncols: int
    nrows: int
    cellsize: float
    origin_x: float
    origin_y: float

    # Ensure both datasets align spatially before computation
    def __eq__(self, other: object) -> bool:
        """Equals method for AscFootprint.

        Takes into account floating point rounding
        by using math.isclose() for float comparisons.

        Args:
            self: AscFootprint
            other: AscFootprint

        Returns:
            bool
        """

        if not isinstance(other, AscFootprint):
            return NotImplemented  # Not implemented for non AscFootprint

        # 'other' is known to be an AscFootprint
        cells_sizes_match = self.cellsize == other.cellsize
        origins_match = math.isclose(self.origin_x, other.origin_x) and math.isclose(self.origin_y, other.origin_y)
        rows_match = self.nrows == other.nrows
        cols_match = self.ncols == other.ncols

        return cells_sizes_match and origins_match and rows_match and cols_match


@dataclass(slots=True, frozen=True)
class AscData:
    # class AscData(AscDataLocation):
    """A data class representing an ASC file's header and data (pd.DataFrame)."""

    data: pd.DataFrame
    ncols: int
    nrows: int
    cellsize: float
    nodata_value: str
    header_case: AscLowerLeft

    xllcorner: float | None = None
    yllcorner: float | None = None
    xllcenter: float | None = None
    yllcenter: float | None = None

    def __post_init__(self):
        """After construction verifies integrity."""

        if self.data is None:
            raise ValueError("Data frame is None.")

        if self.ncols is None or self.ncols <= 0:
            raise ValueError("Zero or negative or none column count")

        if self.nrows is None or self.nrows <= 0:
            raise ValueError("Zero or negative row count")

        if self.cellsize is None or self.cellsize <= 0:
            raise ValueError("Zero or negative cell size")

        if (self.data.shape[0] != self.nrows) or (self.data.shape[1] != self.ncols):
            raise ValueError("Data frame shape doesn't match nrows and/or ncols.")

        if self.header_case is None or self.header_case == AscLowerLeft.INVALID:
            raise ValueError("Zero or negative cell size")

        corners_none = self.xllcorner is None or self.yllcorner is None
        centers_none = self.xllcenter is None or self.yllcenter is None
        if corners_none and centers_none:
            raise ValueError("Lower left center or corner should be defined")

    @property
    def footprint(self) -> AscFootprint:
        """Footprint property.

        Returns:
            AscFootprint
        """
        o = self.origin
        return AscFootprint(self.ncols, self.nrows, self.cellsize, o[0], o[1])

    @property
    def origin(self) -> tuple[float, float]:
        """Origin property, the center (always the center) of lower left cell.

        Returns:
            tuple[float, float] representing x and y of the center (always the center) of lower left cell.
        """
        # Geo3D treats the center of the lower left cell as the origin when reading the project.json,
        # it then immediately subtracts half the cell size to get the true bounding box.

        if self.header_case == AscLowerLeft.CORNERS:
            if self.xllcorner is None or self.yllcorner is None:
                raise ValueError("xllcorner and yllcorner are both None")

            origin_x: float = self.xllcorner + (self.cellsize / 2.0)
            origin_y: float = self.yllcorner + (self.cellsize / 2.0)
        else:
            if self.xllcenter is None or self.yllcenter is None:
                raise ValueError("xllcenter and yllcenter are both None")

            origin_x: float = self.xllcenter
            origin_y: float = self.yllcenter

        return origin_x, origin_y

    # Function to read and process an ASC file object (testable)
    @staticmethod
    def read_asc(source: asc_to_g3d.io.ReadableSource) -> AscData:  # noqa - complexity
        """Read an ASC file from a ReadableSource.

        Args:
            source: ReadableSource

        Returns:
            AscData if successful

        Raises:
            ValueError: Invalid or inconsistent data within the file.
            IOError: An error occurred accessing the file.
        """

        with asc_to_g3d.io.source_to_stream(source) as source_stream:
            # Continue with source_stream
            ncols = None
            nrows = None
            nodata_value = None
            cellsize = None
            xllcorner = None
            yllcorner = None
            xllcenter = None
            yllcenter = None

            prefixes = [
                "ncols",
                "nrows",
                "nodata_value",
                "cellsize",
                "xllcorner",
                "yllcorner",
                "xllcenter",
                "yllcenter",
            ]

            skip_count = 0

            for line in source_stream:
                stripped = line.strip()
                skip_count += 1
                if not stripped:
                    continue  # skip
                elif stripped.lower().startswith(tuple(prefixes)):  # header
                    parts = stripped.split()
                    if len(parts) == 2:
                        keyword, value = parts
                        if keyword.casefold() == "ncols".casefold():
                            ncols = int(value)
                        elif keyword.casefold() == "nrows".casefold():
                            nrows = int(value)
                        elif keyword.casefold() == "nodata_value".casefold():
                            nodata_value = value
                        elif keyword.casefold() == "cellsize".casefold():
                            cellsize = int(float(value))
                        elif keyword.casefold() == "xllcorner".casefold():
                            xllcorner = int(round(float(value)))
                        elif keyword.casefold() == "yllcorner".casefold():
                            yllcorner = float(round(float(value)))
                        elif keyword.casefold() == "xllcenter".casefold():
                            xllcenter = int(round(float(value)))
                        elif keyword.casefold() == "yllcenter".casefold():
                            yllcenter = float(round(float(value)))
                else:  # assume end of header
                    skip_count -= 1  # go back one line, the first line after header will break out of loop
                    break  # break out of loop, data section will be read by pandas

            # check for None
            ncols = rnn(ncols)
            nrows = rnn(nrows)
            nodata_value = rnn(nodata_value)
            cellsize = rnn(cellsize)

            header_ok, corners_ok, centers_ok = AscData._is_valid_header(
                ncols, nrows, nodata_value, cellsize, xllcorner, yllcorner, xllcenter, yllcenter
            )

            # to use centers or corners
            if corners_ok and not centers_ok:
                header_case = AscLowerLeft.CORNERS
            elif centers_ok and not corners_ok:
                header_case = AscLowerLeft.CENTERS
            else:
                header_case = AscLowerLeft.INVALID  # invalid (both or neither)

            # head not valid
            if not header_ok:
                raise ValueError("Header integrity check failed, abort reading file")
            else:  # header is ok, read data using pandas
                # we have already read the first line of the data, that was used to break out of the loop,
                # go back to start of the file and skip header rows.
                source_stream.seek(0)

                # pandas picks up exactly where the cursor is currently resting ∴ use: skiprows=skip_count,
                data: pd.DataFrame = pd.read_csv(
                    source_stream,
                    sep=r"\s+",
                    skiprows=skip_count,
                    skip_blank_lines=True,
                    header=None,
                    na_values=[rnn(nodata_value)],
                )  # noqa
                if nodata_value is not None:
                    data = data.mask(np.isclose(data, float(nodata_value)))

                logger.debug(f" data shape: {data.shape}")
                logger.debug(f" rows: {nrows}")
                logger.debug(f" cols: {ncols}")

                shape_and_header_match = data.shape[0] == nrows and data.shape[1] == ncols

                if not shape_and_header_match:
                    raise ValueError(
                        f"Header and data dimensions do not match, rows: {nrows}, cols: {ncols}, shape: {data.shape}"
                    )

            asc = AscData(
                data=data,
                ncols=ncols,
                nrows=nrows,
                nodata_value=nodata_value,
                cellsize=cellsize,
                xllcorner=xllcorner,
                yllcorner=yllcorner,
                xllcenter=xllcenter,
                yllcenter=yllcenter,
                header_case=header_case,
            )

            logger.debug(f"  ASC data = {data.shape}")
            logger.debug(f"  ASC ncols = {ncols}")
            logger.debug(f"  ASC nrows = {nrows}")
            logger.debug(f"  ASC nodata_value = {nodata_value}")
            logger.debug(f"  ASC cellsize = {cellsize}")
            logger.debug(f"  ASC xllcorner = {xllcorner}")
            logger.debug(f"  ASC yllcorner = {yllcorner}")
            logger.debug(f"  ASC xllcenter = {xllcenter}")
            logger.debug(f"  ASC yllcenter = {yllcenter}")
            logger.debug(f"  ASC header_case = {header_case.value}")

            return asc

    @staticmethod
    def _is_valid_header(
        ncols: int, nrows: int, nodata_value: str, cellsize: int, xllcorner, yllcorner, xllcenter, yllcenter
    ) -> tuple[bool, bool, bool]:
        """Internal static method for checking header data is valid.

        Header must have nrows, ncols, cellsize and nodata value.
        Header must have either: xllcorner & yllcorner OR xllcenter & yllcenter.

        Returns:
            Tuple[bool, bool, bool], header is ok, corners ok, centers ok.
        """

        structure_ok = all(value is not None for value in [ncols, nrows, cellsize, nodata_value])
        positive_values = ncols > 0 and nrows > 0 and cellsize > 0
        corners_ok = xllcorner is not None and yllcorner is not None
        centers_ok = xllcenter is not None and yllcenter is not None
        centers_or_corners_ok = (corners_ok or centers_ok) and not (corners_ok and centers_ok)
        all_ok = centers_or_corners_ok and structure_ok and positive_values

        if not all_ok:
            logger.error(f"Header integrity check failed, structure OK: {structure_ok and positive_values}")
            logger.error(f"Header integrity check failed, corners OK: {corners_ok}")
            logger.error(f"Header integrity check failed, centers OK: {centers_ok}")
            logger.error(f"Header integrity check failed, centers or corners OK: {centers_or_corners_ok}")
            logger.error(f"Header integrity check failed, overall OK: {all_ok}")

        return all_ok, corners_ok, centers_ok
