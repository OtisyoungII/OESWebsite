"""Build a static ICO derived from the procedural OES Core geometry and palette."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'oes_core_launcher' / 'assets' / 'oes-eyeball.ico'


def frame(size):
    scale = size / 256
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    glow = Image.new('RGBA', image.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((25*scale, 25*scale, 231*scale, 231*scale), fill=(56,189,248,90))
    glow = glow.filter(ImageFilter.GaussianBlur(max(1, int(14*scale))))
    image.alpha_composite(glow)
    d = ImageDraw.Draw(image)
    d.ellipse((20*scale, 70*scale, 236*scale, 186*scale), outline=(56,189,248,180), width=max(1,int(3*scale)))
    d.ellipse((42*scale, 42*scale, 214*scale, 214*scale), fill=(6,20,38,255), outline=(125,211,252,210), width=max(1,int(4*scale)))
    d.ellipse((75*scale, 75*scale, 181*scale, 181*scale), fill=(56,189,248,255))
    d.ellipse((91*scale, 91*scale, 165*scale, 165*scale), fill=(34,197,94,230))
    d.ellipse((105*scale, 105*scale, 151*scale, 151*scale), fill=(1,3,10,255), outline=(56,189,248,170), width=max(1,int(3*scale)))
    if size >= 48:
        try:
            font = ImageFont.truetype('arialbd.ttf', max(7, int(12*scale)))
        except OSError:
            font = ImageFont.load_default()
        box = d.textbbox((0, 0), 'OES', font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        d.text(((size-width)/2, (size-height)/2-box[1]), 'OES', font=font,
               fill=(226, 232, 240, 235))
    d.ellipse((62*scale, 55*scale, 112*scale, 76*scale), fill=(255,255,255,75))
    return image


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    images = [frame(size) for size in sizes]
    images[-1].save(OUTPUT, format='ICO', append_images=images[:-1], sizes=[(x,x) for x in sizes])
    print(OUTPUT)


if __name__ == '__main__':
    main()
