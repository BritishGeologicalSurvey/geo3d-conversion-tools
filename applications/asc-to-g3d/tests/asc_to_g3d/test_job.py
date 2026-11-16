"""Tests for job.py.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Literal

import pytest

from asc_to_g3d.job import Job


def _make_a_path(name="file.txt") -> Path:
    """Helper function to create a Path."""
    return Path(name)


def test_valid_with_all_inputs() -> None:
    """Test Job constructor with valid inputs."""
    job = Job(
        layer_name="layer1",
        top=_make_a_path("top"),
        base=_make_a_path("base"),
        thickness=_make_a_path("thickness"),
        g3d_output=_make_a_path("out.g3d"),
        strict=True,
        thickness_threshold=0.5,
    )

    assert job.layer_name == "layer1"
    assert job.has_top()
    assert job.has_base()
    assert job.has_thickness()


def test_valid_with_top_and_base_only():
    """Test Job constructor with valid top and base only."""

    job = Job(
        layer_name="layer1",
        top=_make_a_path("top"),
        base=_make_a_path("base"),
        thickness=None,
        g3d_output=_make_a_path("out.g3d"),
        strict=False,
        thickness_threshold=0,
    )

    assert job.has_top()
    assert job.has_base()
    assert not job.has_thickness()


def test_valid_with_top_and_thickness_only():
    """Test Job constructor with valid top and thickness only."""

    job = Job(
        layer_name="layer1",
        top=_make_a_path("top"),
        base=None,
        thickness=_make_a_path("thickness"),
        g3d_output=_make_a_path("out.g3d"),
        strict=False,
        thickness_threshold=0,
    )

    assert job.has_top()
    assert not job.has_base()
    assert job.has_thickness()


def test_valid_with_base_and_thickness_only():
    """Test Job constructor with valid base and thickness only."""

    job = Job(
        layer_name="layer1",
        top=None,
        base=_make_a_path("base"),
        thickness=_make_a_path("thickness"),
        g3d_output=_make_a_path("out.g3d"),
        strict=False,
        thickness_threshold=0,
    )

    assert not job.has_top()
    assert job.has_base()
    assert job.has_thickness()


@pytest.mark.parametrize(
    "top, base, thickness",
    [
        (None, None, None),
        (_make_a_path("top"), None, None),
        (None, _make_a_path("base"), None),
        (None, None, _make_a_path("thickness")),
    ],
)
def test_requires_at_least_two_inputs(top: None | Path, base: None | Path, thickness: None | Path):
    """Test error raised when none or only one of (top, base, thickness) is supplied."""

    with pytest.raises(ValueError, match="need at least two of: top, base, thickness"):
        Job(
            layer_name="layer1",
            top=top,
            base=base,
            thickness=thickness,
            g3d_output=_make_a_path("out.g3d"),
            strict=True,
            thickness_threshold=0,
        )


@pytest.mark.parametrize("layer", ["", "   ", None])
def test_invalid_layer(layer: None | Literal[""] | Literal["   "]):
    """Test error raised when an invalid layer name is supplied."""

    with pytest.raises(ValueError, match="Layer name must be a non-empty string"):
        Job(
            layer_name=layer,
            top=_make_a_path("top"),
            base=_make_a_path("base"),
            thickness=_make_a_path("thickness"),
            g3d_output=_make_a_path("out.g3d"),
            strict=True,
            thickness_threshold=0,
        )


def test_g3d_output_required():
    """Test error raised when output path is not supplied."""
    with pytest.raises(ValueError, match="G3D output must be provided"):
        Job(
            layer_name="layer1",
            top=_make_a_path("top"),
            base=_make_a_path("base"),
            thickness=_make_a_path("thickness"),
            g3d_output=None,  # noqa - this is what we want to test
            strict=True,
            thickness_threshold=0,
        )


@pytest.mark.parametrize("value", [-1, -0.0001])
def test_negative_threshold(value: float | Literal[-1]):
    """Test error negative threshold is supplied."""

    with pytest.raises(ValueError, match="Thickness threshold must be non-negative"):
        Job(
            layer_name="layer1",
            top=_make_a_path("top"),
            base=_make_a_path("base"),
            thickness=_make_a_path("thickness"),
            g3d_output=_make_a_path("out.g3d"),
            strict=True,
            thickness_threshold=value,
        )


def test_zero_threshold():
    """Test thickness threshold of ZERO is acceptable."""

    job = Job(
        layer_name="layer1",
        top=_make_a_path("top"),
        base=_make_a_path("base"),
        thickness=_make_a_path("thickness"),
        g3d_output=_make_a_path("out.g3d"),
        strict=True,
        thickness_threshold=0,
    )
    assert job is not None  # i.e. no errors raised


def test_immutable():
    """Test Job is immutable."""

    job = Job(
        layer_name="layer1",
        top=_make_a_path("top"),
        base=_make_a_path("base"),
        thickness=_make_a_path("thickness"),
        g3d_output=_make_a_path("out.g3d"),
        strict=True,
        thickness_threshold=0.5,
    )

    with pytest.raises(FrozenInstanceError, match="cannot assign to field 'layer_name'"):
        job.layer_name = "new_layer"  # type: ignore - we want to test immutability
