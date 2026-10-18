"""Draw the app icon (a sprout on deep green) at the sizes phones need."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"
S = 1024
GREEN, CREAM, LEAF = (47, 107, 69), (247, 243, 234), (124, 198, 144)


def leaf(size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([0, size * 0.3, size, size * 0.7], fill=color)
    return im


img = Image.new("RGBA", (S, S), GREEN + (255,))
d = ImageDraw.Draw(img)
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=0, fill=GREEN)
# stem
d.line([(S * .5, S * .80), (S * .5, S * .40)], fill=CREAM, width=int(S * .045))
d.ellipse([S * .3, S * .76, S * .7, S * .84], fill=CREAM)  # soil mound
# leaves
top = (S * .5, S * .47)  # top of the stem, where both leaves attach
L = leaf(int(S * .40), LEAF).rotate(-38, expand=True, resample=Image.BICUBIC)   # tip up-left
R = leaf(int(S * .40), CREAM).rotate(38, expand=True, resample=Image.BICUBIC)   # tip up-right
img.alpha_composite(L, (int(top[0] - L.width * .86), int(top[1] - L.height * .86)))
img.alpha_composite(R, (int(top[0] - R.width * .14), int(top[1] - R.height * .86)))

OUT.mkdir(parents=True, exist_ok=True)
for size, name in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png"), (32, "favicon-32.png")]:
    img.convert("RGB").resize((size, size), Image.LANCZOS).save(OUT / name)
print("icons written to", OUT)
