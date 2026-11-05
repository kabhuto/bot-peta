import sys, os, math, sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
png, pgw, gpkg = sys.argv[1:4]
nums = [int(v) for v in sys.argv[4].split(",")]
HALF = int(os.environ.get("HALF", 260))
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
c = sqlite3.connect(gpkg)
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
im = Image.open(png).convert("RGB")
font = ImageFont.truetype("arial.ttf", 20)
for n in nums:
    r = c.execute(f'select geotag_latitude,geotag_longitude from "{t}" where cast(no_bang as integer)=?', (n,)).fetchone()
    cx, cy = to_px(*r)
    box = (int(cx - HALF), int(cy - HALF), int(cx + HALF), int(cy + HALF))
    cr = im.crop(box); d = ImageDraw.Draw(cr)
    d.ellipse([HALF - 9, HALF - 9, HALF + 9, HALF + 9], outline=(255, 255, 0), width=3)
    cr = cr.rotate(90, expand=True)
    ImageDraw.Draw(cr).text((6, 4), f"gpkg {n:04d} (lingkaran kuning, posisi GPS asli)", fill=(255, 255, 0), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
    cr.save(os.path.join(SCR, f"around_{n}.jpg"), quality=90)
    print(n, "px", round(cx), round(cy))
