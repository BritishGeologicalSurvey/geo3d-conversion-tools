"""Represents an ASC to G3D conversion job.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

from __future__ import annotations

from dataclasses import dataclass

import asc_to_g3d.io


@dataclass(frozen=True, slots=True)
class Job:
    """Represents an ASC to G3D conversion job."""

    layer_name: str | None
    top: asc_to_g3d.io.ReadableSource | None
    base: asc_to_g3d.io.ReadableSource | None
    thickness: asc_to_g3d.io.ReadableSource | None
    g3d_output: asc_to_g3d.io.WritableTarget | None
    strict: bool
    thickness_threshold: float

    def __post_init__(self) -> None:
        """After construction verifies integrity."""

        if not isinstance(self.layer_name, str) or not self.layer_name.strip():
            raise ValueError("Layer name must be a non-empty string.")

        provided_count = sum([self.has_top(), self.has_base(), self.has_thickness()])

        if provided_count < 2:
            raise ValueError(
                f"Invalid job: only {provided_count} inputs provided, need at least two of: top, base, thickness."
            )

        if self.g3d_output is None:
            raise ValueError("G3D output must be provided")

        if self.thickness_threshold < 0:
            raise ValueError("Thickness threshold must be non-negative.")

    # --- Simple presence checks ---
    def has_top(self) -> bool:
        """Has top data file path?

        Returns:
            bool
        """
        return self.top is not None

    def has_base(self) -> bool:
        """Has base data file path?

        Returns:
            bool
        """
        return self.base is not None

    def has_thickness(self) -> bool:
        """Has thickness data file path?

        Returns:
            bool
        """
        return self.thickness is not None
