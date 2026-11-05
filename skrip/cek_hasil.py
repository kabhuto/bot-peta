"""Gambar hasil akhir di atas peta scan supaya mudah dicek: python cek_hasil.py <desa> <sls> "<peta>" x0 y0 w h [skala]

Titik hasil (yang sudah dipindah) digambar sebagai lingkaran kecil + nomor gpkg; hijau = dipindah, kuning = dipindah_cek.
Koordinat x0,y0,w,h dalam piksel peta.  Keluaran: cek_<sls>.jpg di folder skrip.
"""
import os, sys, math, sqlite3, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
ROOT = r"D:\bot peta"; SCR = os.path.dirname(os.path.abspath(__file__))
desa, sls, peta = sys.argv[1:4]; x0, y0, w, h = [int(v) for v in sys.argv[4:8]]; sk = float(sys.argv[8]) if len(sys.argv) > 8 else 2.0
png = os.path.join(ROOT, "geo", desa, peta + "_WSS.png")
A, D, B, E, C, F = [float(x) for x in open(png[:-4] + ".pgw").read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
def px(lon, lat):
    x = lon * 6378137.0 * math.pi / 180.0; y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
im = Image.open(png).convert("RGB").crop((x0, y0, x0 + w, y0 + h)).resize((int(w * sk), int(h * sk)), Image.LANCZOS)
d = ImageDraw.Draw(im); font = ImageFont.truetype("arialbd.ttf", 15)
c = sqlite3.connect(os.path.join(ROOT, desa, f"3526020{desa}{sls}_rapi_parkir.gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
for nb, g, st in c.execute(f'select no_bang,geom,status_pindah from "{t}"'):
    if st not in ("dipindah", "dipindah_cek"): continue
    lon, lat = struct.unpack("<dd", g[13:29]); u, v = px(lon, lat)
    if not (x0 <= u < x0 + w and y0 <= v < y0 + h): continue
    a, b = (u - x0) * sk, (v - y0) * sk; col = (0, 200, 0) if st == "dipindah" else (255, 190, 0)
    d.ellipse([a - 5, b - 5, a + 5, b + 5], outline=col, width=3); d.text((a + 7, b - 18), str(int(nb)), fill=col, font=font)
out = os.path.join(SCR, f"cek_{sls}.jpg"); im.save(out, quality=90); print(out)
