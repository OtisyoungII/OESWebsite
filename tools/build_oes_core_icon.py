"""Compose launcher assets around the existing OES Website Eyeball artwork."""
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'oes_core_launcher' / 'assets'
WEBSITE_EYEBALL = ROOT / 'static' / 'images' / 'oes-logo.svg'
# Lossless 220x220 rasterization of WEBSITE_EYEBALL for Pillow/ICO output.
EYEBALL_RENDER = ASSETS / 'source' / 'oes-eyeball-source.png'
EXPECTED_WEBSITE_EYEBALL_SHA256 = (
    '1ce89e6864b8d5799d4806228a3f71172f5bd3c7adaba7d1c8772127d702032b'
)
ICON = ASSETS / 'oes-eyeball.ico'
BASEBALL_LAUNCH = ASSETS / 'eyeball-baseball-launch.png'
BASE_LAUNCH = ASSETS / 'eyeball-base-launch.png'
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def verify_source():
    digest = hashlib.sha256(WEBSITE_EYEBALL.read_bytes()).hexdigest()
    if digest != EXPECTED_WEBSITE_EYEBALL_SHA256:
        raise ValueError(
            'The website Eyeball changed; refresh the lossless render before rebuilding icons.'
        )
    with Image.open(EYEBALL_RENDER) as image:
        if image.size != (220, 220) or image.mode != 'RGBA':
            raise ValueError('The website Eyeball render must remain a 220x220 RGBA image.')


def aspect_fit_eyeball(size, occupancy):
    """Resize proportionally and center; never crop, stretch, or restyle Eyeball."""
    with Image.open(EYEBALL_RENDER) as source:
        eyeball = source.convert('RGBA')
    target = max(1, round(size * occupancy))
    eyeball.thumbnail((target, target), Image.Resampling.LANCZOS)
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    layer.alpha_composite(eyeball, ((size - eyeball.width) // 2, (size - eyeball.height) // 2))
    return layer


def glass_container(size):
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    inset = max(1, round(size * .035))
    radius = max(3, round(size * .22))
    draw.rounded_rectangle(
        (inset, inset, size - inset - 1, size - inset - 1),
        radius=radius,
        fill=(3, 15, 31, 235),
        outline=(93, 211, 255, 145),
        width=max(1, round(size * .018)),
    )
    if size >= 32:
        draw.arc(
            (round(size * .09), round(size * .07), round(size * .91), round(size * .82)),
            200, 330, fill=(220, 248, 255, 75), width=max(1, round(size * .012)),
        )
    return layer


def _font(size):
    for path in (
        Path('C:/Windows/Fonts/arialbd.ttf'),
        Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def baseball_bat(size, detail=True, label=False, offset=.07):
    """Draw only the new bat artwork on an otherwise transparent layer."""
    bat = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bat)
    cy = size // 2
    barrel_height = max(2, round(size * (.105 if detail else .085)))
    handle_height = max(1, round(barrel_height * .52))
    start, grip_end, end = round(size * .035), round(size * .32), round(size * .95)
    draw.rounded_rectangle(
        (grip_end, cy - barrel_height // 2, end, cy + barrel_height // 2),
        radius=max(1, barrel_height // 2), fill=(218, 142, 49, 255),
        outline=(255, 218, 139, 230) if detail else None,
        width=max(1, round(size * .008)),
    )
    draw.rounded_rectangle(
        (start, cy - handle_height // 2, grip_end + 2, cy + handle_height // 2),
        radius=max(1, handle_height // 2), fill=(15, 37, 67, 255),
    )
    knob = max(2, round(barrel_height * .65))
    draw.ellipse(
        (start - knob // 3, cy - knob // 2, start + knob, cy + knob // 2),
        fill=(218, 142, 49, 255),
    )
    if detail:
        draw.line(
            (round(size * .42), cy - round(barrel_height * .22),
             round(size * .84), cy - round(barrel_height * .22)),
            fill=(255, 226, 158, 115), width=max(1, round(size * .008)),
        )
    if label and size >= 128:
        font = _font(max(8, round(size * .052)))
        text_box = draw.textbbox((0, 0), 'OES', font=font)
        text_width = text_box[2] - text_box[0]
        draw.text(
            (round(size * .66) - text_width // 2, cy - (text_box[3] - text_box[1]) // 2),
            'OES', font=font, fill=(47, 28, 14, 235),
        )
    rotated = bat.rotate(38, resample=Image.Resampling.BICUBIC, center=(cy, cy))
    positioned = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    shift = round(size * offset)
    positioned.alpha_composite(rotated, (shift, -shift))
    return positioned


def tiny_bat_accent(size):
    """Keep the original Eyeball dominant at 16–32px."""
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    width = max(2, round(size * .085))
    start = (round(size * .63), round(size * .32))
    end = (round(size * .92), round(size * .07))
    draw.line((start, end), fill=(226, 151, 55, 255), width=width)
    radius = max(1, width // 2)
    for x, y in (start, end):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=(226, 151, 55, 255))
    return layer


def impact_highlight(size):
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = round(size * .76), round(size * .29)
    radius = max(1, round(size * .035))
    draw.line((x - radius, y, x + radius, y), fill=(238, 252, 255, 210), width=1)
    draw.line((x, y - radius, x, y + radius), fill=(238, 252, 255, 210), width=1)
    return layer


def icon_frame(size):
    canvas = glass_container(size)
    eyeball_occupancy = .68 if size >= 48 else .74
    canvas.alpha_composite(aspect_fit_eyeball(size, eyeball_occupancy))
    if size <= 32:
        canvas.alpha_composite(tiny_bat_accent(size))
    else:
        canvas.alpha_composite(baseball_bat(size, detail=size >= 48, label=size >= 128))
    if size >= 48:
        canvas.alpha_composite(impact_highlight(size))
    return canvas


def launch_frame(with_bat):
    size = 512
    # Both launch states use identical Eyeball pixels at identical placement.
    canvas = aspect_fit_eyeball(size, .7)
    if with_bat:
        canvas.alpha_composite(baseball_bat(size, detail=True, label=True, offset=.11))
        canvas.alpha_composite(impact_highlight(size))
    return canvas


def main():
    verify_source()
    ASSETS.mkdir(parents=True, exist_ok=True)
    frames = [icon_frame(size) for size in ICON_SIZES]
    frames[-1].save(
        ICON, format='ICO', append_images=frames[:-1], sizes=[(x, x) for x in ICON_SIZES]
    )
    launch_frame(False).save(BASE_LAUNCH)
    launch_frame(True).save(BASEBALL_LAUNCH)
    print(ICON)


if __name__ == '__main__':
    main()
