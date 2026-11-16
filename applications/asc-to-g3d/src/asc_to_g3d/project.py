"""Project JSON creation.
© UKRI (British Geological Survey) and the Polish Geological Institute 2026.
"""

import colorsys
import json
import logging
import math
from collections.abc import Generator
from datetime import datetime
from typing import Any

from asc_to_g3d import configuration
from asc_to_g3d.g3d import G3DBoundsXY, G3DBoundsXYZ
from asc_to_g3d.io import ReadableSource
from asc_to_g3d.types import require_not_none as rnn

type JSONObject = dict[str, Any]
type JSONList = list[Any]
type JSON = JSONObject | JSONList

logger = logging.getLogger(__name__)


def to_string(data: JSON, indent: int = 4, sort_keys=True, ignore_none=False) -> str:
    """Convert JSON data to str."""
    obj = strip_none(data, True, True) if ignore_none else data
    return json.dumps(obj=obj, indent=indent, sort_keys=sort_keys)


def strip_none(data: Any, dicts: bool = True, lists: bool = True) -> Any:
    """Recursively removes None values from Python data structures.

    Arguments:
        data: The input dictionary, list, or primitive value.
        dicts: If True, removes keys with None values from dictionaries.
        lists: If True, removes None elements from lists.

    Returns:
        the data with "None" removed depending on  the arguments
    """
    if isinstance(data, dict):
        # dict
        return {
            key: strip_none(value, dicts, lists)
            for key, value in data.items()
            # if value is None and dicts == True, then it will be excluded
            if not (dicts and value is None)
        }
    elif isinstance(data, list):
        # list
        return [
            strip_none(item, dicts, lists)
            for item in data
            # if item is None and lists == True, then it will be excluded
            if not (lists and item is None)
        ]
    return data


def make_multilingual(**kwargs: str) -> JSONObject:
    """Create a multilingual object.
    example: make_multilingual(en="sand", pl="piasek").
    """
    # The Pythonic way to pass arbitrary key-value pairs to a function without
    # passing a dictionary object is by using keyword arguments (**kwargs).

    # Enforce type at runtime
    for key, value in kwargs.items():
        if not isinstance(value, str):
            raise TypeError(f"Value for '{key}' must be a string. Got {type(value).__name__} instead.")

    return kwargs


def make_layer(
    layer_id: int,
    layer_name: str,
    layer_group_id: int,
    voxel_group_id: int,
    weight: int,
    geological_unit: str | None,
    color_hex: str = "#0088FF",
) -> JSONObject:
    """Create a layer model."""

    label_en: str = f"{layer_name}{f' ({geological_unit})' if geological_unit is not None else ''}"
    label: JSONObject = make_multilingual(en=label_en)

    source: JSONObject = {
        "format": "geus",
        "type": "sgrid",
        "dataType": "text",
        "voxelId": voxel_group_id,
        "indices": f"assets/{layer_name}.g3d",
        "zScale": 1,
        # "positions":None, noqa
        # "bufferSize":None, noqa
        # "parameters":None, noqa
    }

    return {
        "id": layer_id,
        "label": label,
        "groupId": layer_group_id,
        "src": source,
        "weight": weight,
        "type": "model",
        "autoload": True,
        "color": color_hex,
        # "data":None,
        # "parameters":None, noqa
        # "infoId":None, noqa
        # "merge":None,  noqa
        # "isVolumeless":None, noqa
        # "noData":None, noqa
    }


def make_min_max_bbox(min_x: float, min_y: float, min_z: float, max_x: float, max_y: float, max_z: float) -> JSONObject:
    """Create bbox."""

    min_xyz: JSONObject = {"x": min_x, "y": min_y, "z": min_z}
    max_xyz: JSONObject = {"x": max_x, "y": max_y, "z": max_z}

    return {"min": min_xyz, "max": max_xyz}


def make_voxel_group(voxel_group_id: int, origin_x: float, origin_y: float, cellsize: float) -> JSONObject:
    """Create voxel group."""

    return {
        "id": voxel_group_id,
        "origin": [origin_x, origin_y],
        "zScale": 1.0,
        "aoEnabled": False,
        "borderEnabled": False,
        "depthShading": 0.5,
        "size": [cellsize, cellsize],
        "noData": None,
    }


def make_layer_group(layer_group_id: int, layer_group_name: str, weight: int = 0) -> JSONObject:
    """Create a layer group for group_id."""

    label_en: str = layer_group_name
    label: JSONObject = make_multilingual(en=label_en)

    return {
        "id": layer_group_id,
        "label": label,
        "type": "group",
        "weight": weight,
        "groupId": None,  # to support nested groups I assume
        "autoload": True,
        # "isVolumeless":None, noqa
        # "noData":None, noqa
        # "color":None, noqa
        # "merge":None, noqa
    }


def make_voxel_groups(voxel_groups: list[tuple[G3DBoundsXY, int]]) -> JSONList:
    """Create voxel groups list."""
    voxel_groups_list: JSONList = []

    for footprint, voxel_group_id in voxel_groups:
        vg = make_voxel_group(voxel_group_id, footprint.origin_x, footprint.origin_y, footprint.cellsize)
        voxel_groups_list.append(vg)

    return voxel_groups_list


def get_spacing(data_range, target=5):
    """Calculate a suitable spacing for the data range with a target number of spaces."""
    if data_range == 0:
        return 1

    raw_spacing = data_range / target
    exponent = math.floor(math.log10(raw_spacing))
    fraction = raw_spacing / (10**exponent)

    # Map to the closest nice round numbers (1, 2, 2.5, 5, 10)
    if fraction < 1.5:
        round_fraction = 1.0
    elif fraction < 2.25:
        round_fraction = 2.0
    elif fraction < 3.75:
        round_fraction = 2.5
    elif fraction < 7.5:
        round_fraction = 5.0
    else:
        round_fraction = 10.0

    return round_fraction * (10**exponent)


def get_grid_spacing(
    bbox: JSONObject, vertical_target: int = 5, horizontal_target: int = 5
) -> None | tuple[float, float]:
    """Calculate a suitable grid spacing for the bbox."""

    if (
        bbox["max"] is not None
        and isinstance(bbox["max"]["x"], float)
        and isinstance(bbox["max"]["y"], float)
        and isinstance(bbox["max"]["z"], float)
        and bbox["min"] is not None
        and isinstance(bbox["min"]["x"], float)
        and isinstance(bbox["min"]["y"], float)
        and isinstance(bbox["min"]["z"], float)
    ):
        dx = bbox["max"]["x"] - bbox["min"]["x"]
        dy = bbox["max"]["y"] - bbox["min"]["y"]
        dz = bbox["max"]["z"] - bbox["min"]["z"]
        dxy_min = min(dx, dy)

        vertical_spacing = get_spacing(dz, vertical_target)
        horizontal_spacing = get_spacing(dxy_min, horizontal_target)

        return (horizontal_spacing, vertical_spacing)
    else:
        return None


def make_attributes_list(default_attribute_object_id: int, default_attribute_object_name: str) -> JSONList:
    """Create default attributes list."""

    name: JSONObject = make_multilingual(en=default_attribute_object_name)

    attributes: JSONObject = {
        "id": default_attribute_object_id,
        "type": "discrete",
        "default": True,
        "name": name,
        "weight": 0,
    }

    return [attributes]


def make_project(
    project_id: int,
    title: JSONObject,  # multilingual object
    description: JSONObject,  # multilingual object
    attributes_list: list[JSONObject],
    layers: list[JSONObject],
    voxel_groups: list[JSONObject],
    bbox: JSONObject,
    language: str = "en",
) -> JSONObject:
    """Create a project (root container for layers)."""

    # Project contains Config contains  Global contains Bbox

    global_bbox: JSONObject = {
        "bbox": bbox,
        # "crs":None, noqa
        # "nearPlane":None, noqa
        # "farPlane":None, noqa
        # "antialiasing":None, noqa
        # "constcamtargetdist":None, noqa
        # "oneSideMaterial":None, noqa
        # "lineThreshold":None, noqa
        # "light":None, noqa
        # "slicing":None, noqa
    }

    grid_spacing: tuple[float, float] | None = get_grid_spacing(bbox=bbox)

    features: JSONObject | None = None

    if grid_spacing is not None:
        config_grid: JSONObject = {
            "textSize": 11,
            "boundingOffset": 0,
            "unitX": grid_spacing[0],
            "unitY": grid_spacing[0],
            "unitZ": grid_spacing[1],
            "showOnStart": True,
        }

        toggle: JSONObject = {"state": True, "config": config_grid, "autoload": None, "opacity": None}

        features: JSONObject | None = {"coordGrid": toggle}

    config: JSONObject = {"global": global_bbox, "features": features}

    return {
        "resourceType": "project",
        "id": project_id,
        "title": title,
        "description": description,
        "language": language,
        "layers": layers,
        "voxelGroups": voxel_groups,
        "config": config,
        "attributes": attributes_list,
        # "infos":None, noqa
    }


def infinite_counter(start: int = 0, delta: int = 1) -> Generator[int]:
    """Infinite counter."""
    num = start
    while True:
        yield num
        num += delta


def generate_hex_colors(n: int) -> list[str]:
    """Generates a list of N visually distinct hex color strings."""
    if n <= 0:
        return []

    hex_colors = []
    for i in range(n):
        # Evenly space the hue between 0.0 and 1.0
        hue = i / n

        # Saturation and value high (0.8 - 0.9) for bright, distinct colors
        saturation = 0.8
        value = 0.9

        # Convert HSV to RGB (returns floats between 0.0 and 1.0)
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)

        # Convert RGB floats to integers (0-255) and format as a hex string
        hex_color = f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"
        hex_colors.append(hex_color)

    return hex_colors


def sort_by_weight(layers_and_groups_list: list[JSONObject]) -> list[JSONObject]:
    """Sorts the layers and groups by weight, groups first, then models."""

    type_order = {
        "group": 0,
        "model": 1,
    }

    sorted_layers = sorted(
        layers_and_groups_list,
        key=lambda layer: (
            type_order.get(layer["type"], float("inf")),  # groups first
            layer.get("weight", float("inf")),  # ascending weight
        ),
    )

    return sorted_layers


def make_project_json(  # noqa complexity
    bounded_g3d_list: list[G3DBoundsXYZ], layer_config: ReadableSource | None, verbose: bool = False
) -> str:
    """Each "G3DBoundsXYZ" represents a generated G3D file.

    Args:
        bounded_g3d_list: list[G3DBoundsXYZ] the list of the bounds of G3D files created.
        verbose: bool, if true stack trace for errors will be logged.
        layer_config: asc_to_g3d.io.ReadableSource, optional layer configuration.

    """

    if not bounded_g3d_list:
        raise ValueError("list of layer bounds is empty.")

    # even if None a valid default configuration will be used
    config = configuration.get_layer_configuration(layer_config)

    min_x = float("inf")
    min_y = float("inf")
    min_z = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    max_z = float("-inf")

    unique_id_gen: Generator[int] = infinite_counter()  # used for group and model layers
    voxel_groups: list[tuple[G3DBoundsXY, int]] = []
    layer_list: list[JSONObject] = []
    group_dict: dict[str, tuple[int, int, JSONObject]] = {}  # group name : tuple (group id, group weight, JSONObject)
    hex_colors: list[str] = generate_hex_colors(len(bounded_g3d_list))

    for index, g3d_bounds in enumerate(bounded_g3d_list):
        try:
            layer_name: str = g3d_bounds.layer_name

            # keyed on layer name
            layer_id: int = next(unique_id_gen)
            layer_weight: int = rnn(config.get_weight(layer_name, config.get_unweighted_weight()))
            layer_geological_unit: str | None = config.get_geological_unit(layer_name)
            layer_hex_color: str = rnn(config.get_hex_color(layer_name, hex_colors[index]))
            layer_group_name: str = rnn(config.get_group(layer_name, config.get_ungrouped_group()))

            # if layer_group_name not seen before
            if layer_group_name not in group_dict:
                layer_group_id = next(unique_id_gen)
                group_dict[layer_group_name] = (
                    layer_group_id,
                    layer_weight,  #  use the layer weight for the group weight
                    make_layer_group(
                        layer_group_id=layer_group_id,
                        layer_group_name=layer_group_name,
                        weight=layer_weight,  # use the layer weight for the group weight
                    ),
                )
            else:
                layer_group: tuple[int, int, JSONObject] = group_dict[layer_group_name]
                layer_group_id: int = layer_group[0]
                layer_group_weight: int = layer_group[1]
                layer_group_obj: JSONObject = layer_group[2]
                if layer_weight < layer_group_weight:
                    layer_group_obj["weight"] = (
                        layer_weight  # give the group the same weight as the lowest weighted layer in the group
                    )

            # log config details
            logger.info(f"   Configure Layer = {layer_name}, id: {layer_id}")
            logger.debug(f"   +- group, name = {layer_group_name}, id: = {layer_group_id}")
            logger.debug(f"   +-  colour = {layer_hex_color}")
            logger.debug(f"   +-  geology = {layer_geological_unit}")
            logger.debug(f"   +-  weight = {layer_weight}")

            # determine the voxel group
            # check bounds to see which voxel group it should be grouped with
            voxel_group_id = None
            for bxy, vg in voxel_groups:
                if g3d_bounds.bounds_xy == bxy:  # uses is close within __eq__
                    voxel_group_id = vg
                    break

            # If none, a new voxel group is needed
            if voxel_group_id is None:
                voxel_group_id = next(unique_id_gen)
                voxel_groups.append((g3d_bounds.bounds_xy, voxel_group_id))

            # update minimums and maximums
            min_x = min(min_x, g3d_bounds.bounds_xy.min_x, g3d_bounds.bounds_xy.max_x)
            min_y = min(min_y, g3d_bounds.bounds_xy.min_y, g3d_bounds.bounds_xy.max_y)
            min_z = min(min_z, g3d_bounds.min_z, g3d_bounds.max_z)

            max_x = max(max_x, g3d_bounds.bounds_xy.min_x, g3d_bounds.bounds_xy.max_x)
            max_y = max(max_y, g3d_bounds.bounds_xy.min_y, g3d_bounds.bounds_xy.max_y)
            max_z = max(max_z, g3d_bounds.min_z, g3d_bounds.max_z)

            # prepare project json
            layer_model: JSONObject = make_layer(
                layer_id=layer_id,
                layer_group_id=layer_group_id,
                voxel_group_id=voxel_group_id,
                layer_name=layer_name,
                weight=layer_weight,
                geological_unit=layer_geological_unit,
                color_hex=rnn(layer_hex_color),
            )
            layer_list.append(layer_model)
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Unexpected processing error {error_type} occurred: {e}", exc_info=verbose)

    voxel_groups_list = make_voxel_groups(voxel_groups)

    bbox: JSONObject = make_min_max_bbox(min_x=min_x, min_y=min_y, min_z=min_z, max_x=max_x, max_y=max_y, max_z=max_z)

    # combine group and layer lists into one
    layers_and_groups_list: list[JSONObject] = []
    layers_and_groups_list.extend([value[2] for value in group_dict.values()])
    layers_and_groups_list.extend(layer_list)

    # sort layers and groups
    sorted_layers_and_groups_list = sort_by_weight(layers_and_groups_list)

    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    config_name = config.get_name()
    name: str = (
        f"asc-to-g3d ({formatted_time})" if config_name is None else f"asc-to-g3d from {config_name} ({formatted_time})"
    )

    attributes_list = make_attributes_list(next(unique_id_gen), name)

    description_en: str = (
        f"Generated by asc-to-g3d ({formatted_time})"
        if config_name is None
        else f"Generated by asc-to-g3d from {config_name} ({formatted_time})"
    )
    description: JSONObject = make_multilingual(en=description_en)

    title_en: str = f"asc-to-g3d ({formatted_time})" if config_name is None else f"{config_name} ({formatted_time})"
    title: JSONObject = make_multilingual(en=title_en)

    project = make_project(
        project_id=0,
        title=title,
        description=description,
        attributes_list=attributes_list,
        layers=sorted_layers_and_groups_list,
        voxel_groups=voxel_groups_list,
        bbox=bbox,
    )

    # write overall json structure
    return to_string(project, ignore_none=True)
