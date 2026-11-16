"""Tests for g3d.py.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

from typing import cast

import pytest

from asc_to_g3d.g3d import G3DBoundsXY


def make_bounds(**overrides):
    """Helper function to create G3DBounds."""
    base: dict[str, float | int] = dict(
        ncols=10,
        nrows=20,
        cellsize=1.0,
        origin_x=100.0,
        origin_y=200.0,
        min_x=100.0,
        max_x=110.0,
        min_y=200.0,
        max_y=220.0,
    )
    base.update(overrides)
    return G3DBoundsXY(**cast(dict, base))


def test_eq_requires_same_rows_and_cols():
    """Test __eq__ when rows and columns differ."""
    a = make_bounds()
    b = make_bounds(nrows=a.nrows + 1)
    c = make_bounds(ncols=a.ncols + 1)

    assert a != b
    assert a != c


@pytest.mark.parametrize(
    "field,value",
    [
        ("min_x", 999.0),
        ("max_x", 999.0),
        ("min_y", 999.0),
        ("max_y", 999.0),
        ("origin_x", 999.0),
        ("origin_y", 999.0),
    ],
)
def test_eq_detects_individual_field_mismatch(field, value):
    """Test __eq__ when individual fields differ."""
    a = make_bounds()
    b = make_bounds(**{field: value})
    assert a != b


def test_eq_with_non_g3dbounds_returns_notimplemented_and_behaves_false():
    """Test __eq__ with object types."""
    a = make_bounds()

    class Dummy:
        pass

    # Direct call to __eq__ shows NotImplemented
    assert a.__eq__(Dummy()) is NotImplemented

    # Using == should resolve to False
    assert (a == Dummy()) is False


def test_eq_symmetry():
    """Test __eq__ is symmetrical."""
    a = make_bounds()
    b = make_bounds(origin_x=a.origin_x + 1e-9)
    assert a == b
    assert b == a


def test_eq_reflexive():
    """Test __eq__ is reflexive."""
    a = make_bounds()
    assert a == a


def test_eq_transitive_within_tolerance():
    """Test __eq__ within small tolerance."""
    eps = 1e-9
    a = make_bounds()
    b = make_bounds(origin_x=a.origin_x + eps)
    c = make_bounds(origin_x=b.origin_x + eps)

    # All still within tolerance window
    assert a == b
    assert b == c
    assert a == c


def test_eq_identical_objects():
    """Test __eq__ with identical objects."""
    a = make_bounds()
    b = make_bounds()
    assert a == b


def test_eq_float_tolerance_with_isclose():
    """Test __eq__ within small tolerance in all float fields."""
    eps = 1e-9
    a = make_bounds()
    b = make_bounds(
        origin_x=a.origin_x + eps,
        origin_y=a.origin_y - eps,
        min_x=a.min_x + eps,
        max_x=a.max_x - eps,
        min_y=a.min_y + eps,
        max_y=a.max_y - eps,
    )
    assert a == b


def test_eq_fails_when_float_outside_tolerance():
    """Test __eq__ returns false when outside of tolerance."""
    delta = 1e-4
    a = make_bounds()
    b = make_bounds(origin_x=a.origin_x + delta)
    assert a != b
