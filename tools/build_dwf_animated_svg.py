"""
===============================================================================
FILE: tools/build_dwf_animated_svg.py

PURPOSE:
    Create an animated Drinks With Friendz SVG from the clean layered master SVG.

UPDATED:
    July 15, 2026

INPUT:
    static/images/drinkz-logo.svg

OUTPUT:
    static/images/drinkz-logo-animated.svg

RESPONSIBILITIES:
    [x] Preserve Deleana's original logo paths
    [x] Preserve original colors and proportions
    [x] Add subtle cyan neon glow to the glass
    [x] Add realistic intermittent neon flicker to the lime
    [x] Add restrained glow to the original lettering
    [x] Add gentle hover brightness
    [x] Support reduced-motion preferences
    [x] Avoid changing or redesigning the logo

IMPORTANT RULES:
    [x] No color replacement
    [x] No path reshaping
    [x] No logo redesign
    [x] Animation enhances presentation only
===============================================================================
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT
    / "static"
    / "images"
    / "drinkz-logo.svg"
)

OUTPUT_FILE = (
    ROOT
    / "static"
    / "images"
    / "drinkz-logo-animated.svg"
)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

ET.register_namespace("", SVG_NAMESPACE)
ET.register_namespace("xlink", XLINK_NAMESPACE)


def svg_tag(name: str) -> str:
    return f"{{{SVG_NAMESPACE}}}{name}"


def require_input_file() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "\nMissing master logo SVG:\n"
            f"{INPUT_FILE}\n\n"
            "Run this first:\n"
            "python tools/build_dwf_svg.py\n"
        )


def find_group(
    root: ET.Element,
    group_id: str,
) -> ET.Element:
    group = root.find(
        f".//{svg_tag('g')}[@id='{group_id}']"
    )

    if group is None:
        raise RuntimeError(
            f"Required SVG group was not found: {group_id}"
        )

    return group


def create_filter(
    definitions: ET.Element,
    filter_id: str,
    blur_amount: str,
    glow_color: str,
    glow_opacity: str,
) -> None:
    neon_filter = ET.SubElement(
        definitions,
        svg_tag("filter"),
        {
            "id": filter_id,
            "x": "-40%",
            "y": "-40%",
            "width": "180%",
            "height": "180%",
            "color-interpolation-filters": "sRGB",
        },
    )

    blur = ET.SubElement(
        neon_filter,
        svg_tag("feGaussianBlur"),
        {
            "in": "SourceGraphic",
            "stdDeviation": blur_amount,
            "result": "blurred-source",
        },
    )

    flood = ET.SubElement(
        neon_filter,
        svg_tag("feFlood"),
        {
            "flood-color": glow_color,
            "flood-opacity": glow_opacity,
            "result": "glow-color",
        },
    )

    composite = ET.SubElement(
        neon_filter,
        svg_tag("feComposite"),
        {
            "in": "glow-color",
            "in2": "blurred-source",
            "operator": "in",
            "result": "colored-glow",
        },
    )

    merge = ET.SubElement(
        neon_filter,
        svg_tag("feMerge"),
    )

    ET.SubElement(
        merge,
        svg_tag("feMergeNode"),
        {
            "in": "colored-glow",
        },
    )

    ET.SubElement(
        merge,
        svg_tag("feMergeNode"),
        {
            "in": "SourceGraphic",
        },
    )


def create_drop_shadow_filter(
    definitions: ET.Element,
) -> None:
    shadow_filter = ET.SubElement(
        definitions,
        svg_tag("filter"),
        {
            "id": "dwf-logo-shadow",
            "x": "-30%",
            "y": "-30%",
            "width": "160%",
            "height": "170%",
            "color-interpolation-filters": "sRGB",
        },
    )

    ET.SubElement(
        shadow_filter,
        svg_tag("feDropShadow"),
        {
            "dx": "0",
            "dy": "70",
            "stdDeviation": "65",
            "flood-color": "#000000",
            "flood-opacity": "0.42",
        },
    )


def create_lime_reflection_filter(
    definitions: ET.Element,
) -> None:
    reflection_filter = ET.SubElement(
        definitions,
        svg_tag("filter"),
        {
            "id": "dwf-lime-reflection",
            "x": "-60%",
            "y": "-60%",
            "width": "220%",
            "height": "220%",
            "color-interpolation-filters": "sRGB",
        },
    )

    blur = ET.SubElement(
        reflection_filter,
        svg_tag("feGaussianBlur"),
        {
            "stdDeviation": "52",
            "result": "lime-reflection-blur",
        },
    )

    color_matrix = ET.SubElement(
        reflection_filter,
        svg_tag("feColorMatrix"),
        {
            "in": "lime-reflection-blur",
            "type": "matrix",
            "values": (
                "0 0 0 0 0.611 "
                "0 0 0 0 0.847 "
                "0 0 0 0 0.259 "
                "0 0 0 0.48 0"
            ),
            "result": "lime-reflection-color",
        },
    )

    merge = ET.SubElement(
        reflection_filter,
        svg_tag("feMerge"),
    )

    ET.SubElement(
        merge,
        svg_tag("feMergeNode"),
        {
            "in": "lime-reflection-color",
        },
    )


def add_definitions(
    root: ET.Element,
) -> ET.Element:
    definitions = ET.Element(
        svg_tag("defs"),
    )

    create_filter(
        definitions=definitions,
        filter_id="dwf-glass-neon",
        blur_amount="42",
        glow_color="#29A8E8",
        glow_opacity="0.72",
    )

    create_filter(
        definitions=definitions,
        filter_id="dwf-lime-neon",
        blur_amount="48",
        glow_color="#9CD842",
        glow_opacity="0.84",
    )

    create_filter(
        definitions=definitions,
        filter_id="dwf-drinkz-glow",
        blur_amount="24",
        glow_color="#FFF27A",
        glow_opacity="0.42",
    )

    create_filter(
        definitions=definitions,
        filter_id="dwf-with-glow",
        blur_amount="18",
        glow_color="#FFFFFF",
        glow_opacity="0.32",
    )

    create_filter(
        definitions=definitions,
        filter_id="dwf-friendz-glow",
        blur_amount="24",
        glow_color="#F89A22",
        glow_opacity="0.42",
    )

    create_drop_shadow_filter(definitions)
    create_lime_reflection_filter(definitions)

    style = ET.SubElement(
        definitions,
        svg_tag("style"),
        {
            "type": "text/css",
        },
    )

    style.text = """
        .dwf-logo {
            overflow: visible;
        }

        .dwf-logo__artwork {
            transform-box: fill-box;
            transform-origin: center;
            transition:
                filter 280ms ease,
                transform 420ms cubic-bezier(.2, .8, .2, 1);
        }

        .dwf-logo:hover .dwf-logo__artwork {
            transform: translateY(-12px) scale(1.012);
            filter: brightness(1.08);
        }

        .dwf-layer {
            transform-box: fill-box;
            transform-origin: center;
        }

        #dwf-glass {
            filter: url(#dwf-glass-neon);
            animation:
                dwfGlassBreathe
                4.8s
                ease-in-out
                infinite;
        }

        #dwf-lime {
            filter: url(#dwf-lime-neon);
            animation:
                dwfLimeNeon
                8.6s
                linear
                infinite;
        }

        #dwf-drinkz {
            filter: url(#dwf-drinkz-glow);
            animation:
                dwfLetteringBreathe
                5.4s
                ease-in-out
                infinite;
        }

        #dwf-with {
            filter: url(#dwf-with-glow);
        }

        #dwf-friendz {
            filter: url(#dwf-friendz-glow);
            animation:
                dwfFriendzBreathe
                5.8s
                ease-in-out
                infinite;
        }

        .dwf-logo__lime-reflection {
            opacity: 0.34;
            filter: url(#dwf-lime-reflection);
            transform:
                translate(230px, 190px)
                scale(1.09);
            transform-box: fill-box;
            transform-origin: center;
            animation:
                dwfLimeReflection
                8.6s
                linear
                infinite;
            pointer-events: none;
        }

        .dwf-logo__floor-reflection {
            opacity: 0.18;
            filter: blur(22px);
            transform:
                translateY(13220px)
                scaleY(-0.13);
            transform-origin: center;
            pointer-events: none;
        }

        @keyframes dwfGlassBreathe {
            0%,
            100% {
                opacity: 0.94;
                filter:
                    url(#dwf-glass-neon)
                    brightness(0.98);
            }

            50% {
                opacity: 1;
                filter:
                    url(#dwf-glass-neon)
                    brightness(1.16);
            }
        }

        @keyframes dwfLetteringBreathe {
            0%,
            100% {
                filter:
                    url(#dwf-drinkz-glow)
                    brightness(1);
            }

            50% {
                filter:
                    url(#dwf-drinkz-glow)
                    brightness(1.08);
            }
        }

        @keyframes dwfFriendzBreathe {
            0%,
            100% {
                filter:
                    url(#dwf-friendz-glow)
                    brightness(1);
            }

            50% {
                filter:
                    url(#dwf-friendz-glow)
                    brightness(1.07);
            }
        }

        /*
        Realistic neon behavior:
        Mostly stable with two short electrical interruptions.
        The lime never remains off.
        */

        @keyframes dwfLimeNeon {
            0%,
            7%,
            10%,
            13%,
            49%,
            52%,
            55%,
            100% {
                opacity: 1;
                filter:
                    url(#dwf-lime-neon)
                    brightness(1.18)
                    saturate(1.08);
            }

            8% {
                opacity: 0.42;
                filter:
                    url(#dwf-lime-neon)
                    brightness(0.58);
            }

            9% {
                opacity: 0.9;
                filter:
                    url(#dwf-lime-neon)
                    brightness(1.02);
            }

            11% {
                opacity: 0.2;
                filter:
                    url(#dwf-lime-neon)
                    brightness(0.38);
            }

            12% {
                opacity: 0.84;
                filter:
                    url(#dwf-lime-neon)
                    brightness(0.94);
            }

            50% {
                opacity: 0.56;
                filter:
                    url(#dwf-lime-neon)
                    brightness(0.7);
            }

            51% {
                opacity: 0.96;
                filter:
                    url(#dwf-lime-neon)
                    brightness(1.1);
            }

            53% {
                opacity: 0.3;
                filter:
                    url(#dwf-lime-neon)
                    brightness(0.48);
            }

            54% {
                opacity: 0.9;
                filter:
                    url(#dwf-lime-neon)
                    brightness(1);
            }
        }

        @keyframes dwfLimeReflection {
            0%,
            7%,
            10%,
            13%,
            49%,
            52%,
            55%,
            100% {
                opacity: 0.34;
            }

            8%,
            11%,
            50%,
            53% {
                opacity: 0.08;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .dwf-logo__artwork,
            #dwf-glass,
            #dwf-lime,
            #dwf-drinkz,
            #dwf-friendz,
            .dwf-logo__lime-reflection {
                animation: none !important;
                transition: none !important;
            }

            .dwf-logo:hover .dwf-logo__artwork {
                transform: none;
            }
        }
    """

    root.insert(0, definitions)

    return definitions


def copy_title_and_description(
    source_root: ET.Element,
    output_root: ET.Element,
) -> None:
    source_title = source_root.find(
        svg_tag("title")
    )

    source_description = source_root.find(
        svg_tag("desc")
    )

    if source_title is not None:
        output_root.append(
            deepcopy(source_title)
        )
    else:
        title = ET.SubElement(
            output_root,
            svg_tag("title"),
            {
                "id": "dwf-animated-logo-title",
            },
        )
        title.text = "Drinks With Friendz"

    if source_description is not None:
        output_root.append(
            deepcopy(source_description)
        )
    else:
        description = ET.SubElement(
            output_root,
            svg_tag("desc"),
            {
                "id": "dwf-animated-logo-description",
            },
        )
        description.text = (
            "Animated Drinks With Friendz logo with a subtle "
            "neon glass glow and realistic lime flicker."
        )


def create_reflection(
    artwork: ET.Element,
    output_root: ET.Element,
) -> None:
    reflection_group = ET.SubElement(
        output_root,
        svg_tag("g"),
        {
            "class": "dwf-logo__floor-reflection",
            "aria-hidden": "true",
        },
    )

    for child in artwork:
        reflection_group.append(
            deepcopy(child)
        )


def create_lime_reflection(
    lime_group: ET.Element,
    output_root: ET.Element,
) -> None:
    lime_reflection = ET.SubElement(
        output_root,
        svg_tag("g"),
        {
            "class": "dwf-logo__lime-reflection",
            "aria-hidden": "true",
        },
    )

    for child in lime_group:
        lime_reflection.append(
            deepcopy(child)
        )


def build_animated_logo() -> None:
    require_input_file()

    source_tree = ET.parse(
        INPUT_FILE
    )
    source_root = source_tree.getroot()

    output_attributes = {
        "id": "drinks-with-friendz-animated-logo",
        "class": "dwf-logo",
        "viewBox": source_root.get(
            "viewBox",
            "0 0 15000 15000",
        ),
        "preserveAspectRatio": source_root.get(
            "preserveAspectRatio",
            "xMidYMid meet",
        ),
        "role": "img",
        "aria-label": (
            "Animated Drinks With Friendz logo"
        ),
    }

    output_root = ET.Element(
        svg_tag("svg"),
        output_attributes,
    )

    add_definitions(
        output_root
    )

    copy_title_and_description(
        source_root,
        output_root,
    )

    artwork = ET.SubElement(
        output_root,
        svg_tag("g"),
        {
            "class": "dwf-logo__artwork",
            "filter": "url(#dwf-logo-shadow)",
        },
    )

    source_layer_ids = (
        "dwf-glass",
        "dwf-lime",
        "dwf-drinkz",
        "dwf-with",
        "dwf-friendz",
    )

    copied_layers: dict[str, ET.Element] = {}

    for layer_id in source_layer_ids:
        source_group = find_group(
            source_root,
            layer_id,
        )

        copied_group = deepcopy(
            source_group
        )

        artwork.append(
            copied_group
        )

        copied_layers[layer_id] = copied_group

    create_lime_reflection(
        copied_layers["dwf-lime"],
        output_root,
    )

    create_reflection(
        artwork,
        output_root,
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_tree = ET.ElementTree(
        output_root
    )

    try:
        ET.indent(
            output_tree,
            space="    ",
        )
    except AttributeError:
        pass

    output_tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print()
    print("Created animated Drinks With Friendz SVG:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    build_animated_logo()