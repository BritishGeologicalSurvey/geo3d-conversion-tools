"""Module for representing different aspects of G3D files as needed by the converter.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import math
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class G3DBoundsXY:
    """Represents the XY bounds of a generated G3D."""

    ncols: int
    nrows: int
    cellsize: float
    origin_x: float  # not the same as min x
    origin_y: float  # not the same as min y
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    # Ensure both datasets align spatially before computation
    def __eq__(self, other: object) -> bool:
        """Equals method for G3DFootprint.

        Takes into account floating point rounding
        by using math.isclose() for float comparisons.

        Args:
            self: G3DBounds
            other: G3DBounds

        Returns:
            bool
        """

        if not isinstance(other, G3DBoundsXY):
            return NotImplemented  # Not implemented for non G3DFootprint

        # 'other' is known to be an G3DBounds
        cells_sizes_match = self.cellsize == other.cellsize
        origins_match = math.isclose(self.origin_x, other.origin_x) and math.isclose(self.origin_y, other.origin_y)
        x_match = math.isclose(self.min_x, other.min_x) and math.isclose(self.max_x, other.max_x)
        y_match = math.isclose(self.min_y, other.min_y) and math.isclose(self.max_y, other.max_y)
        rows_match = self.nrows == other.nrows
        cols_match = self.ncols == other.ncols

        return cells_sizes_match and origins_match and rows_match and cols_match and x_match and y_match


@dataclass(slots=True, frozen=True)
class G3D:
    """Represents the output of the G3D conversion process."""

    file_content: str
    min_z: float
    max_z: float


@dataclass(slots=True, frozen=True)
class G3DBoundsXYZ:
    """Represents the XYZ bounds of a generated G3D."""

    bounds_xy: G3DBoundsXY
    min_z: float
    max_z: float
    layer_name: str
