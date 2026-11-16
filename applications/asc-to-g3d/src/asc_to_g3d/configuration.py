"""Reading and representation of layer configuration: colours, geology etc.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import logging
from dataclasses import dataclass
from typing import cast

import pandas as pd

import asc_to_g3d.io

logger = logging.getLogger(__name__)


class LayersConfiguration:
    """."""

    def get_name(self) -> str | None:
        """Get config name."""
        return "asc-to-g3d"  # default,  "asc-to-g3d"

    def get_layer_names(self) -> list[str]:
        """Get layer names."""
        return []  # default, empty list

    def get_geological_unit(self, _layer_name: str, default: str | None = None) -> str | None:
        """Get geological unit."""
        return default  # default, None

    def get_weight(self, _layer_name: str, default: int | None = None) -> int | None:
        """Get layer weight."""
        return default  # default, None

    def get_unweighted_weight(self) -> int:
        """Get the weight for layers that haven't a specific weight."""
        return 0

    def get_group(self, _layer_name: str, default: str | None = None) -> str | None:
        """Get layer group name."""
        return default  # default, None

    def get_ungrouped_group(self) -> str:
        """Get the group for layers that haven't a specific group."""
        return "default_group"

    def get_rgb_color(
        self, _layer_name: str, default: tuple[int, int, int] | None = None
    ) -> tuple[int, int, int] | None:
        """Get RGB colour."""
        return default  # default, None

    def get_hex_color(self, _layer_name: str, default: str | None = None) -> str | None:
        """Get hexadecimal colour."""
        return default  # default, None


@dataclass(slots=True, frozen=True)
class DataFrameLayersConfiguration(LayersConfiguration):
    """A data class representing the footprint of an ASC file's grid."""

    data: pd.DataFrame
    name: str | None

    def get_name(self) -> str | None:
        """Get config name."""
        return self.name

    def get_layer_names(self) -> list[str]:
        """Get layer names."""
        return self.data["name"].tolist()

    def get_geological_unit(self, layer_name: str, default: str | None = None) -> str | None:
        """Get geological unit."""
        filtered = self.data.loc[self.data["name"] == layer_name, "geological_unit"]

        if filtered.empty:
            return default

        value = filtered.iloc[0]

        if pd.isna(value) or value is None:
            return default

        return str(value)

    def get_weight(self, layer_name: str, default: int | None = None) -> int | None:
        """Get layer weight."""
        filtered = self.data.loc[self.data["name"] == layer_name, "weight"]

        if filtered.empty:
            return default

        value = filtered.iloc[0]

        if pd.isna(value) or value is None:
            return default

        return int(value)

    def get_unweighted_weight(self) -> int:
        """Get the weight for layers that haven't a specific weight."""
        # Check if the column exists and has any data
        if "weight" in self.data.columns and not self.data["weight"].dropna().empty:
            # Find the maximum value and add 1
            max_val = cast(float, self.data["weight"].max())
            return int(max_val) + 1
        else:
            # Fallback if the column is missing or completely empty
            return super().get_unweighted_weight()

    def get_group(self, layer_name: str, default: str | None = None) -> str | None:
        """Get layer group."""
        filtered = self.data.loc[self.data["name"] == layer_name, "group"]

        if filtered.empty:
            return default

        value = filtered.iloc[0]

        if pd.isna(value) or value is None:
            return default

        return str(value)

    def get_ungrouped_group(self) -> str:
        """Get the group for layers that haven't a specific group."""
        # Check if the column exists and has any data
        if "group" in self.data.columns:
            existing_strings = set(self.data["group"].dropna())

            counter = 1
            default = "default_group"

            # Keep incrementing until we find a free string
            while default in existing_strings:
                counter += 1
                default = f"default_group_{counter}"

            return default
        else:
            # Fallback if the column is missing or completely empty
            return super().get_ungrouped_group()

    def get_rgb_color(
        self, layer_name: str, default: tuple[int, int, int] | None = None
    ) -> tuple[int, int, int] | None:
        """Get RGB colour."""
        # Filter for your specific row
        filtered = self.data.loc[self.data["name"] == layer_name]

        if not filtered.empty:
            # Extract values from the first matching row (.iloc[0])
            r = filtered["r"].iloc[0]
            g = filtered["g"].iloc[0]
            b = filtered["b"].iloc[0]

            if pd.isna(r) or r is None or pd.isna(g) or g is None or pd.isna(b) or b is None:
                return default
            else:
                return (int(r), int(g), int(b))
        else:
            return default

    def get_hex_color(self, layer_name: str, default: str | None = None) -> str | None:
        """Get hexadecimal colour."""
        rgb: tuple[int, int, int] | None = self.get_rgb_color(layer_name=layer_name)

        if rgb is None:
            return default

        return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"


def default_layer_configuration() -> LayersConfiguration:
    """Returns an "empty" default implementation."""
    return LayersConfiguration()  # defaults, empty


def read_layer_configuration(source: asc_to_g3d.io.ReadableSource) -> LayersConfiguration:
    """Read a tab separated CSV-like layer configuration file."""

    filename = asc_to_g3d.io.get_filename(source)

    source_stream = asc_to_g3d.io.source_to_stream(source)
    data: pd.DataFrame = pd.read_csv(
        source_stream,
        sep=r"[\t]",
        skipinitialspace=True,
        skip_blank_lines=True,
        quotechar='"',
        header=0,
        engine="python",
    )

    # Clean the column headers (lowercase, strip whitespace and quotes)
    data.columns = data.columns.str.strip().str.replace(r'^"+|"+$', "", regex=True).str.lower()  # noqa pipes

    # Clean the string values in the dataframe (strip whitespace and any stray quotes)
    # We use select_dtypes to only target string columns
    string_cols = data.select_dtypes(include=["object"]).columns
    for col in string_cols:
        data[col] = data[col].astype(str).str.strip().str.replace(r'^"+|"+$', "", regex=True)

    return DataFrameLayersConfiguration(data, filename)


def get_layer_configuration(source: asc_to_g3d.io.ReadableSource | None) -> LayersConfiguration:
    """Get the layer configuration, returning an empty one if the source is None."""
    layer_config: LayersConfiguration
    if source is not None:
        layer_config = read_layer_configuration(source)
    else:
        layer_config = default_layer_configuration()
    return layer_config
