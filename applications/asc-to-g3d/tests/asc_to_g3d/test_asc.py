"""Tests for asc.py.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import io
import math
from dataclasses import FrozenInstanceError

import pytest

from asc_to_g3d.asc import AscData, AscFootprint


def test_read_top_data(mock_top_data: io.StringIO) -> None:
    """Test to read valid top data."""

    asc = AscData.read_asc(mock_top_data)
    assert asc is not None
    assert asc.ncols == 4
    assert asc.nrows == 5
    assert math.isclose(asc.cellsize, 30.0)
    assert asc.xllcenter == 10000
    assert asc.yllcenter == 20000
    assert asc.nodata_value == "-9999"


def test_read_base_data(mock_base_data: io.StringIO) -> None:
    """Test to read valid base data."""

    asc = AscData.read_asc(mock_base_data)
    assert asc is not None
    assert asc.ncols == 4
    assert asc.nrows == 5
    assert math.isclose(asc.cellsize, 30.0)
    assert asc.xllcenter == 10000
    assert asc.yllcenter == 20000
    assert asc.nodata_value == "-9999"


def test_read_data_with_whitespace(mock_data_with_whitespace: io.StringIO) -> None:
    """Test to read valid data with whitespace."""

    asc = AscData.read_asc(mock_data_with_whitespace)
    assert asc is not None
    assert asc.ncols == 4
    assert asc.nrows == 5
    assert math.isclose(asc.cellsize, 30.0)
    assert asc.xllcenter == 10000
    assert asc.yllcenter == 20000
    assert asc.nodata_value == "-9999"


def test_read_data_with_incorrect_nrows_ncols(mock_data_with_incorrect_nrows_ncols: io.StringIO) -> None:
    """Test to check error raised when incorrect rows / columns detected."""

    with pytest.raises(ValueError) as exc_info:
        AscData.read_asc(mock_data_with_incorrect_nrows_ncols)
    assert "data dimensions do not match" in str(exc_info.value)


def test_read_data_with_corners_and_centers(mock_data_with_corners_and_centers: io.StringIO) -> None:
    """Test to check error raised when both corners and centers are detected."""

    with pytest.raises(ValueError) as exc_info:
        AscData.read_asc(mock_data_with_corners_and_centers)
    assert "integrity check failed" in str(exc_info.value)


def test_read_data_with_one_corner_and_one_centers(mock_data_with_one_corner_and_one_centers: io.StringIO) -> None:
    """Test to check error raised when one corner and one center is detected."""

    with pytest.raises(ValueError) as exc_info:
        AscData.read_asc(mock_data_with_one_corner_and_one_centers)
    assert "integrity check failed" in str(exc_info.value)


def test_data_dimensions(mock_top_data: io.StringIO) -> None:
    """Test to confirm columns and rows are as expected from valid data."""

    asc = AscData.read_asc(mock_top_data)
    assert asc is not None
    assert asc.ncols == 4
    assert asc.nrows == 5

    shape = asc.data.shape
    assert asc.nrows == shape[0]
    assert asc.ncols == shape[1]


def test_footprint_with_centers(mock_data_with_centers: io.StringIO) -> None:
    """Test to confirm centers are as expected from valid data using centers."""

    asc = AscData.read_asc(mock_data_with_centers)
    assert asc is not None
    assert asc.xllcenter == 10000
    assert asc.yllcenter == 20000

    footprint = asc.footprint
    assert footprint is not None

    assert math.isclose(footprint.cellsize, 30.0)
    assert footprint.nrows == 5
    assert footprint.ncols == 4
    assert footprint.origin_x == 10000
    assert footprint.origin_y == 20000


def test_origin_with_centers(mock_data_with_centers: str) -> None:
    """Test to confirm origin is calculated as expected from valid data using centers."""

    asc = AscData.read_asc(mock_data_with_centers)
    assert asc is not None
    assert asc.xllcenter == 10000
    assert asc.yllcenter == 20000

    origin = asc.origin
    assert origin is not None

    assert origin[0] == 10000
    assert origin[1] == 20000


def test_footprint_with_corners(mock_data_with_corners: str) -> None:
    """Test to confirm corners are as expected from valid data using corners."""

    asc = AscData.read_asc(mock_data_with_corners)
    assert asc is not None
    assert asc.xllcorner == 11111
    assert asc.yllcorner == 22222

    footprint = asc.footprint
    assert footprint is not None

    assert math.isclose(footprint.cellsize, 30.0)
    assert footprint.nrows == 5
    assert footprint.ncols == 4
    assert footprint.origin_x == 11111 + (footprint.cellsize / 2.0)
    assert footprint.origin_y == 22222 + (footprint.cellsize / 2.0)


def test_origin_with_corners(mock_data_with_corners: str) -> None:
    """Test to confirm origin is calculated as expected from valid data using corners."""

    asc = AscData.read_asc(mock_data_with_corners)
    assert asc is not None
    assert asc.xllcorner == 11111
    assert asc.yllcorner == 22222

    cell = asc.cellsize
    origin = asc.origin
    assert origin is not None

    assert origin[0] == 11111 + (cell / 2.0)
    assert origin[1] == 22222 + (cell / 2.0)


def test_asc_data_immutable(mock_top_data: str) -> None:
    """Test to AscData is immutable."""

    asc: AscData = AscData.read_asc(mock_top_data)
    assert asc is not None

    with pytest.raises(FrozenInstanceError, match="cannot assign to field 'cellsize'"):
        asc.cellsize = 100  # type: ignore - we want to test immutability


def test_footprint_immutable(mock_top_data: str) -> None:
    """Test to AscFootprint is immutable."""
    asc: AscData = AscData.read_asc(mock_top_data)
    assert asc is not None

    footprint: AscFootprint = asc.footprint
    assert footprint is not None

    with pytest.raises(FrozenInstanceError, match="cannot assign to field 'cellsize'"):
        footprint.cellsize = 100  # type: ignore - we want to test immutability
