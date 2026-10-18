"""Draw the app icon from the pixel sprout sprite in static/sprites.js."""
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "icons"
src = (ROOT / "static" / "sprites.js").read_text()
pal = dict(re.findall(r'(\w): "(#[0-9a-f]{6})"', src.split("const SPRITES")[0]))
rows = re.findall(r'"([^"]+)"', re.search(r"sprout: \[(.*?)\]", src, re.S).group(1))

BG = (255, 241, 220)
grid = 24                                   # 16px sprite centred on a 24px canvas
img = Image.new("RGB", (grid, grid), BG)
off = (grid - 16) // 2
for y, row in enumerate(rows):
    for x, c in enumerate(row):
        if c != ".":
            img.putpixel((x + off, y + off), tuple(int(pal[c][i:i + 2], 16) for i in (1, 3, 5)))

OUT.mkdir(parents=True, exist_ok=True)
for size, name in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png"), (32, "favicon-32.png")]:
    img.resize((size, size), Image.NEAREST).save(OUT / name)
print("icons written")
