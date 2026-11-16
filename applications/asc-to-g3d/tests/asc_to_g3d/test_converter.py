"""Tests for converter.py.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import ast
import io
from math import isclose

import pytest

import asc_to_g3d.converter as converter
from asc_to_g3d.asc import AscData
from asc_to_g3d.job import Job


def test_convert_asc_to_g3d_inc_project_json(
    mock_top_data: str, mock_base_data: str, expected_g3d_data: list, pgi_ui_tool_data_no_abs: list
):
    """Test that G3D content can be generated and written to a temporary file.

    Args:
        mock_top_data: str
        mock_base_data: str
        expected_g3d_data: list
        pgi_ui_tool_data_no_abs: list (to compare to)
    """

    g3d = io.StringIO()
    # Monkeypatch trick Python so calling g3d.close() does absolutely nothing,
    # meaning get_value can be called after convert_asc_to_g3d
    g3d.close = lambda: None

    project_json = io.StringIO()
    # Monkeypatch trick Python so calling g3d.close() does absolutely nothing,
    # meaning get_value can be called after convert_asc_to_g3d
    project_json.close = lambda: None

    job = Job(
        layer_name="layer_name",
        g3d_output=g3d,
        strict=False,
        thickness_threshold=1e-5,
        top=mock_top_data,
        base=mock_base_data,
        thickness=None,
    )

    converter.convert_multiple_asc_to_g3d([job])

    g3d_value = g3d.getvalue()

    assert len(g3d_value) > 0
    assert _compare_nested_helper(_list_to_nested_helper(expected_g3d_data), _str_to_nested_helper(g3d_value))
    assert _compare_nested_helper(_list_to_nested_helper(pgi_ui_tool_data_no_abs), _str_to_nested_helper(g3d_value))

    # TODO test else where
    # project_json_value = project_json.getvalue()
    # assert len(project_json_value) > 0
    # assert '"resourceType": "project"' in project_json_value
    # assert '"x": 9985.0' in project_json_value
    # assert '"y": 19985.0' in project_json_value
    # assert '"z": 102.0' in project_json_value
    # assert '"x": 10105.0' in project_json_value
    # assert '"y": 20135.0' in project_json_value
    # assert '"z": 319.0' in project_json_value
    # assert '"label": "layer_name"' in project_json_value


def test_convert_asc_to_g3d(
    mock_top_data: str, mock_base_data: str, expected_g3d_data: list, pgi_ui_tool_data_no_abs: list
):
    """Test that G3D content can be generated and written to a temporary file.

    Args:
        mock_top_data: str
        mock_base_data: str
        expected_g3d_data: list
        pgi_ui_tool_data_no_abs: list (to compare to)
    """

    g3d = io.StringIO()
    # Monkeypatch trick Python so calling g3d.close() does absolutely nothing,
    # meaning get_value can be called after convert_asc_to_g3d
    g3d.close = lambda: None

    job = Job(
        layer_name="layer_name",
        g3d_output=g3d,
        strict=False,
        thickness_threshold=1e-5,
        top=mock_top_data,
        base=mock_base_data,
        thickness=None,
    )

    converter.convert_asc_to_g3d(job)

    g3d_value = g3d.getvalue()

    assert len(g3d_value) > 0
    assert _compare_nested_helper(_list_to_nested_helper(expected_g3d_data), _str_to_nested_helper(g3d_value))
    assert _compare_nested_helper(_list_to_nested_helper(pgi_ui_tool_data_no_abs), _str_to_nested_helper(g3d_value))


def test_process_data(
    mock_top_data: str, mock_base_data: str, expected_g3d_data: list, pgi_ui_tool_data_no_abs: list
) -> None:
    """Test that G3D content can be generated.

    Args:
        mock_top_data: str
        mock_base_data: str
        expected_g3d_data: list
        pgi_ui_tool_data_no_abs: list (to compare to)
    """
    top_asc = AscData.read_asc(mock_top_data)
    assert top_asc is not None

    base_asc = AscData.read_asc(mock_base_data)
    assert base_asc is not None

    converter.check_same_footprint(base_asc, top_asc)

    thickness_data = top_asc.data - base_asc.data

    g3d = converter.process_data(top_asc.data, base_asc.data, thickness_data, top_asc.nrows, top_asc.ncols)

    assert len(g3d.file_content) > 0
    assert _compare_nested_helper(_list_to_nested_helper(expected_g3d_data), _str_to_nested_helper(g3d.file_content))
    assert _compare_nested_helper(
        _list_to_nested_helper(pgi_ui_tool_data_no_abs), _str_to_nested_helper(g3d.file_content)
    )


def test_process_data_with_strict_nan_check(mock_top_data: str, mock_base_data: str) -> None:
    """Test that an error is raised when strict NaN check is enabled
        and their is a mismatch between the NaNs in the top and base data.

    Args:
        mock_top_data: str
        mock_base_data: str
    """

    top_asc = AscData.read_asc(mock_top_data)
    assert top_asc is not None

    base_asc = AscData.read_asc(mock_base_data)
    assert base_asc is not None

    converter.check_same_footprint(base_asc, top_asc)

    thickness_data = top_asc.data - base_asc.data

    with pytest.raises(ValueError, match="corresponding elements differ"):
        converter.process_data(top_asc.data, base_asc.data, thickness_data, top_asc.nrows, top_asc.ncols, strict=True)


# ======================================================================================================================


# ======================================================================================================================


def _str_to_nested_helper(data: str) -> dict[int, dict[int, tuple[float, float]]]:
    return _list_to_nested_helper(ast.literal_eval(data))


def _list_to_nested_helper(data: list[float | int]) -> dict[int, dict[int, tuple[float, float]]]:

    result: dict[int, dict[int, tuple[float, float]]] = {}
    for i in range(0, len(data), 4):
        x, y, top, base = data[i : i + 4]

        if x not in result:
            result[int(x)] = {}

        result[int(x)][int(y)] = (top, base)

    return result


def _same_keys_helper(a: dict[int, dict], b: dict[int, dict]) -> bool:
    if a.keys() != b.keys():
        return False

    for x in a:
        if a[x].keys() != b[x].keys():
            return False

    return True


def _compare_nested_helper(
    a: dict[int, dict[int, tuple[float, float]]], b: dict[int, dict[int, tuple[float, float]]]
) -> bool:
    a_size = sum(len(inner) for inner in a.values())
    b_size = sum(len(inner) for inner in b.values())
    if a_size != b_size:
        print(f"different length {a_size} and {b_size}")
        return False

    if not _same_keys_helper(a, b):
        print("different keys")
        return False

    for x in a:
        if x not in b:
            print(f"x {x} not in b")
            return False

        for y in a[x]:
            if y not in b[x]:
                print(f"y {y} not in b")
                return False

            a1, a2 = a[x][y]
            b1, b2 = b[x][y]

            ok1 = isclose(a1, b1)
            ok2 = isclose(a2, b2)

            if not (ok1 and ok2):
                print(f"a1 {a1}  b1 {b1}")
                print(f"a2 {a2}  b2 {b2}")
                return False

    return True


def _print_nested_helper(
    a: dict[int, dict[int, tuple[float, float]]], b: dict[int, dict[int, tuple[float, float]]]
) -> None:
    axs = list(a.keys())
    ays = [y for inner in a.values() for y in inner.keys()]

    bxs = list(b.keys())
    bys = [y for inner in b.values() for y in inner.keys()]

    min_x = min(min(axs), min(bxs))
    max_x = max(max(axs), max(bxs))
    min_y = min(min(ays), min(bys))
    max_y = max(max(ays), max(bys))

    print()
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            a0 = "-"
            a1 = "-"
            if x in a and y in a[x]:
                a0 = a[x][y][0]
                a1 = b[x][y][0]

            b0 = "-"
            b1 = "-"
            if x in b and y in b[x]:
                b0 = b[x][y][0]
                b1 = b[x][y][0]

            print(f"x {x:<5} y {y:<5} upper a0 {a0:<10} b0 {b0:<10} lower a0 {a1:<10} b0 {b1:<10}")


def test_compare_pgi_to_cli_output(expected_g3d_data: list, pgi_ui_tool_data_no_abs: list) -> None:
    """Test compares output from PGI notebook with the CLI tool."""

    e = _list_to_nested_helper(expected_g3d_data)
    ui = _list_to_nested_helper(pgi_ui_tool_data_no_abs)

    _print_nested_helper(e, ui)
    same: bool = _compare_nested_helper(e, ui)
    assert same
