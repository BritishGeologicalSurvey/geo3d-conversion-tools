"""Centralised configuration file for the Python Pytest.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

from textwrap import dedent

import pytest


# TOP ASC data
@pytest.fixture(scope="session")
def mock_top_data() -> str:
    """Generates valid mock top data.

    Returns:
        str
    """

    content = dedent("""
        ncols 4
        nrows 5
        xllcenter 10000
        yllcenter 20000
        cellsize 30.0
        nodata_value -9999
        100 101.005 152 203
        104.05 155 206 -9999
        158 209 210 211
        212 -9999 214 215
        016 217 218 319
    """)
    return content


# BASE ASC data
@pytest.fixture(scope="session")
def mock_base_data() -> str:
    """Generates valid mock base data.

    Returns:
        str
    """

    content = dedent("""
        nodata_value -9999
        nrows 5
        yllcenter 20000
        ncols 4
        cellsize 30.0
        xllcenter 10000
        100 101 102 103
        104 105 106 107
        108 109 110 111
        112 -9999 114 115
        116 117 118 119
    """)
    return content


# Whitespace
@pytest.fixture(scope="session")
def mock_data_with_whitespace() -> str:
    """Generates valid data with whitespace.

    Returns:
        str
    """

    content = dedent("""
        nodata_value -9999
            nrows 5
        yllcenter 20000

        ncols 4
        cellsize 30.0
        xllcenter 10000

        100 101 102 103
        104 105 106 107

        108 109 110 111
            112 -9999 114 115
        116 117 118 119
    """)
    return content


# row and col count swapped
@pytest.fixture(scope="session")
def mock_data_with_incorrect_nrows_ncols() -> str:
    """Generates mock data with incorrect row and column sizes.

    Returns:
        str
    """

    content = dedent("""
        ncols 5
        nrows 4
        xllcenter 10000
        yllcenter 20000
        cellsize 30.0
        nodata_value -9999
        100 101.005 152 203
        104.05 155 206 -9999
        158 209 210 211
        212 -9999 214 215
        016 217 218 319
    """)
    return content


# corners and centers
@pytest.fixture(scope="session")
def mock_data_with_corners_and_centers() -> str:
    """Generates mock data with both corners and centers defined.

    Returns:
        str
    """

    content = dedent("""
        ncols 4
        nrows 5
        xllcenter 10000
        yllcenter 20000
        xllcorner 11111
        yllcorner 22222
        cellsize 30.0
        nodata_value -9999
        100 101.005 152 203
        104.05 155 206 -9999
        158 209 210 211
        212 -9999 214 215
        016 217 218 319
    """)
    return content


# corners and centers
@pytest.fixture(scope="session")
def mock_data_with_one_corner_and_one_centers() -> str:
    """Generates mock data with one corner and one center defined.

    Returns:
        str
    """

    content = dedent("""
        ncols 4
        nrows 5
        xllcenter 10000
        yllcorner 22222
        cellsize 30.0
        nodata_value -9999
        100 101.005 152 203
        104.05 155 206 -9999
        158 209 210 211
        212 -9999 214 215
        016 217 218 319
    """)
    return content


# centers
@pytest.fixture(scope="session")
def mock_data_with_centers() -> str:
    """Generates mock data with centers defined.

    Returns:
        str
    """

    content = dedent("""
        ncols 4
        nrows 5
        xllcenter 10000
        yllcenter 20000
        cellsize 30.0
        nodata_value -9999
        100 101.005 152 203
        104.05 155 206 -9999
        158 209 210 211
        212 -9999 214 215
        016 217 218 319
    """)
    return content


# Note the top data and base data when subtracted cover many edge cases:
# negative thickness, zero thickness, near zero thickness, nan in one, nan in both


# corners
@pytest.fixture(scope="session")  # read up on scope
def mock_data_with_corners() -> str:
    """Generates mock data with corners defined.

    Returns:
        str
    """

    content = dedent("""
        ncols 4
        nrows 5
        xllcorner 11111
        yllcorner 22222
        cellsize 30.0
        nodata_value -9999
        100 101.005 152 203
        104.05 155 206 -9999
        158 209 210 211
        212 -9999 214 215
        016 217 218 319
    """)
    return content  # read up on fixtures with yield


# fmt: off
# thickness threshold 0.005
@pytest.fixture(scope="session")
def expected_g3d_data() -> list:
    """Expected output from the CLI tool."""
    return [2, 4, 152.00, 102.00, 3, 4, 203.00, 103.00, 0, 3, 104.05, 104.00, 1, 3, 155.00, 105.00, 2, 3, 206.00, 106.00, 0, 2, 158.00, 108.00, 1, 2, 209.00, 109.00, 2, 2, 210.00, 110.00, 3, 2, 211.00, 111.00, 0, 1, 212.00, 112.00, 2, 1, 214.00, 114.00, 3, 1, 215.00, 115.00, 1, 0, 217.00, 117.00, 2, 0, 218.00, 118.00, 3, 0, 319.00, 119.00]  # noqa


# thickness threshold 0.005
@pytest.fixture(scope="session")
def pgi_ui_tool_data() -> list:
    """Output from PGI notebook, with abs(thickness)."""
    return [2, 4, 152.0, 102.0, 3, 4, 203.0, 103.0, 0, 3, 104.05, 104.0, 1, 3, 155.0, 105.0, 2, 3, 206.0, 106.0, 0, 2, 158.0, 108.0, 1, 2, 209.0, 109.0, 2, 2, 210.0, 110.0, 3, 2, 211.0, 111.0, 0, 1, 212.0, 112.0, 2, 1, 214.0, 114.0, 3, 1, 215.0, 115.0, 0, 0, 16.0, 116.0, 1, 0, 217.0, 117.0, 2, 0, 218.0, 118.0, 3, 0, 319.0, 119.0]  # noqa


# thickness threshold 0.005 and not using abs(top - base)
@pytest.fixture(scope="session")
def pgi_ui_tool_data_no_abs() -> list:
    """Output from PGI notebook, with abs(thickness) replaced with just thickness."""
    return [2, 4, 152.0, 102.0, 3, 4, 203.0, 103.0, 0, 3, 104.05, 104.0, 1, 3, 155.0, 105.0, 2, 3, 206.0, 106.0, 0, 2, 158.0, 108.0, 1, 2, 209.0, 109.0, 2, 2, 210.0, 110.0, 3, 2, 211.0, 111.0, 0, 1, 212.0, 112.0, 2, 1, 214.0, 114.0, 3, 1, 215.0, 115.0, 1, 0, 217.0, 117.0, 2, 0, 218.0, 118.0, 3, 0, 319.0, 119.0]  # noqa
# fmt: on
