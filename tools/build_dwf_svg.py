"""
===============================================================================
FILE: tools/build_dwf_svg.py

PURPOSE:
    Combine the five traced Drinks With Friendz SVG layers into one
    animation-ready master SVG while preserving Potrace transforms.

UPDATED:
    July 15, 2026

OUTPUT:
    static/images/drinkz-logo.svg

LAYERS:
    [x] Martini glass
    [x] Lime
    [x] Drinkz lettering
    [x] With lettering
    [x] Friendz lettering

IMPORTANT:
    The Potrace files must be generated with --invert so the colored artwork,
    not the black background, is traced.
===============================================================================
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
TEMP_DIRECTORY = ROOT / "temp"
OUTPUT_FILE = ROOT / "static" / "images" / "drinkz-logo.svg"

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)

LAYERS = (
    ("glass", "#29A8E8"),
    ("lime", "#9CD842"),
    ("drinkz", "#FFF27A"),
    ("with", "#FFFFFF"),
    ("friendz", "#F89A22"),
)


def svg_tag(name: str) -> str:
    return f"{{{SVG_NAMESPACE}}}{name}"


def recolor_element(element: ET.Element, color: str) -> None:
    """
    Apply the requested brand color to every traced shape while preserving
    Potrace transforms and path geometry.
    """

    if element.tag in {
        svg_tag("path"),
        svg_tag("polygon"),
        svg_tag("polyline"),
        svg_tag("circle"),
        svg_tag("ellipse"),
        svg_tag("rect"),
    }:
        element.set("fill", color)

        if "stroke" in element.attrib and element.attrib["stroke"] != "none":
            element.set("stroke", color)

    element.attrib.pop("style", None)

    for child in element:
        recolor_element(child, color)


def read_layer(layer_name: str, color: str) -> tuple[ET.Element, ET.Element]:
    source_file = TEMP_DIRECTORY / f"{layer_name}.svg"

    if not source_file.exists():
        raise FileNotFoundError(
            f"Missing traced layer: {source_file}\n"
            "Run Potrace with --invert before building the master SVG."
        )

    source_tree = ET.parse(source_file)
    source_root = source_tree.getroot()

    wrapper = ET.Element(
        svg_tag("g"),
        {
            "id": f"dwf-{layer_name}",
            "class": f"dwf-layer dwf-layer--{layer_name}",
            "fill": color,
            "data-dwf-layer": layer_name,
        },
    )

    for child in source_root:
        copied_child = deepcopy(child)
        recolor_element(copied_child, color)
        wrapper.append(copied_child)

    return source_root, wrapper


def build_master_svg() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    first_root: ET.Element | None = None
    wrappers: list[ET.Element] = []

    for layer_name, color in LAYERS:
        source_root, wrapper = read_layer(layer_name, color)

        if first_root is None:
            first_root = source_root

        wrappers.append(wrapper)

    if first_root is None:
        raise RuntimeError("No SVG layers were loaded.")

    output_attributes = {
        "id": "drinks-with-friendz-logo",
        "class": "dwf-logo",
        "viewBox": first_root.get("viewBox", "0 0 15000 15000"),
        "role": "img",
        "aria-labelledby": "dwf-logo-title dwf-logo-description",
        "preserveAspectRatio": "xMidYMid meet",
    }

    output_root = ET.Element(svg_tag("svg"), output_attributes)

    title = ET.SubElement(
        output_root,
        svg_tag("title"),
        {"id": "dwf-logo-title"},
    )
    title.text = "Drinks With Friendz"

    description = ET.SubElement(
        output_root,
        svg_tag("desc"),
        {"id": "dwf-logo-description"},
    )
    description.text = (
        "Drinks With Friendz logo featuring a blue martini glass, "
        "green lime, yellow Drinkz lettering, white with lettering, "
        "and orange Friendz lettering."
    )

    for wrapper in wrappers:
        output_root.append(wrapper)

    output_tree = ET.ElementTree(output_root)

    try:
        ET.indent(output_tree, space="    ")
    except AttributeError:
        pass

    output_tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print()
    print("Created layered Drinks With Friendz SVG:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    build_master_svg()