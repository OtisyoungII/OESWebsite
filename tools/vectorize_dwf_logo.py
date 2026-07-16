"""
===============================================================================
FILE: tools/vectorize_dwf_logo.py

PURPOSE
    Split the Drinks With Friendz logo into individual color masks
    so each piece can be traced into SVG.

OUTPUT

temp/
    glass.pbm
    lime.pbm
    drinkz.pbm
    with.pbm
    friendz.pbm

===============================================================================
"""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "static/images/drinkz-logo.png"

OUTPUT = ROOT / "temp"

OUTPUT.mkdir(exist_ok=True)


img = cv2.imread(str(INPUT))

if img is None:
    raise FileNotFoundError(INPUT)


hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


def save_mask(name, lower, upper):

    mask = cv2.inRange(
        hsv,
        np.array(lower),
        np.array(upper),
    )

    cv2.imwrite(
        str(OUTPUT / f"{name}.pbm"),
        mask,
    )

    print(f"Saved {name}.pbm")


#
# Blue Martini Glass
#

save_mask(
    "glass",
    [90, 80, 80],
    [120, 255, 255],
)

#
# Lime
#

save_mask(
    "lime",
    [40, 80, 80],
    [85, 255, 255],
)

#
# Yellow Drinkz
#

save_mask(
    "drinkz",
    [20, 40, 120],
    [40, 255, 255],
)

#
# White "with"
#

save_mask(
    "with",
    [0, 0, 180],
    [180, 40, 255],
)

#
# Orange Friendz
#

save_mask(
    "friendz",
    [5, 120, 120],
    [20, 255, 255],
)

print()
print("Done.")