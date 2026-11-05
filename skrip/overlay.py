import sqlite3, sys, math, shutil, os, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
gpkg_src, png, pgw, tag = sys.argv[1:5]
gpkg = os.path.join(SCR, tag + ".gpkg")
shutil.copyfile(gpkg_src, gpkg)

A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
M = np.array([[A, B], [D, E]])
Minv = np.linalg.inv(M)

def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    col, row = Minv @ np.array([x - C, y - F])
    return col, row

c = sqlite3.connect(gpkg)
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
rows = c.execute(f'select fid,no_bang,geotag_latitude,geotag_longitude,geotag_accuracy from "{t}"').fetchall()
print("titik:", len(rows), "nomor unik:", len({r[1] for r in rows}))
by = collections.defaultdict(list)
for r in rows:
    by[r[1]].append(r)
print("nomor ganda:", {k: len(v) for k, v in by.items() if len(v) > 1})

im = Image.open(png).convert("RGB")
print("gambar", im.size)
d = ImageDraw.Draw(im)
font = ImageFont.truetype("arial.ttf", 22)
pts = []
for fid, nb, lat, lon, acc in rows:
    col, row = to_px(lat, lon)
    pts.append((nb, col, row))
    dup = len(by[nb]) > 1
    colr = (255, 0, 0) if dup else (0, 255, 255)
    d.ellipse([col - 6, row - 6, col + 6, row + 6], outline=colr, width=3)
    d.text((col + 8, row - 26), str(int(nb)) if nb and nb.isdigit() else str(nb), fill=colr, font=font, stroke_width=2, stroke_fill=(0, 0, 0))
cols = [p[1] for p in pts]; rws = [p[2] for p in pts]
print("bbox px:", min(cols), max(cols), min(rws), max(rws))
im.save(os.path.join(SCR, tag + "_overlay.png"))
im.resize((im.width // 2, im.height // 2)).save(os.path.join(SCR, tag + "_overlay_half.jpg"), quality=88)
