r"""Perbesar satu area peta tegak: python zoom.py <desa> <peta> <id_kandidat|x0,y0,x1,y1> <skala> <keluaran.jpg> [lebar_px]

Kalau argumen ke-3 berupa id kandidat, area diambil di sekitar kandidat itu (lebar_px, default 140 px peta).
Koordinat x,y berada di peta yang sudah ditegakkan (sama dengan luas.py: box ubin). Kandidat digambar merah dengan id-nya.
Hanya untuk dibaca; tidak mengubah apa pun.
"""
import os, sys, json
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SCR)
from tagutil import tag_for
desa, mapname, area, sc, out = sys.argv[1:6]; sc = float(sc)
HW = int(sys.argv[6]) if len(sys.argv) > 6 else 140
tag = tag_for(desa, mapname)
png = os.path.join(r"D:\bot peta", "geo", desa, mapname + "_WSS.png"); pgw = png[:-4] + ".pgw"
A, D = [float(x) for x in open(pgw).read().split()[:2]]
rot = 90 if abs(D) > abs(A) else 0
if rot and D < 0: rot = -90
cand = json.load(open(os.path.join(SCR, tag + "_cand.json")))
im = Image.open(png).convert("RGB"); W, H = im.size
if rot: im = im.rotate(rot, expand=True)
def tr(x, y):
    if rot == -90: return H - 1 - y, x
    if rot == 90: return y, W - 1 - x
    return x, y
P = {c["id"]: tr(c["cx"], c["cy"]) for c in cand}
if "," in area: x0, y0, x1, y1 = [float(v) for v in area.split(",")]
else:
    cx, cy = P[int(area)]; x0, y0, x1, y1 = cx - HW, cy - HW * 0.7, cx + HW, cy + HW * 0.7
x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(im.width, x1), min(im.height, y1)
cr = im.crop((int(x0), int(y0), int(x1), int(y1))); cr = cr.resize((int(cr.width * sc), int(cr.height * sc)), Image.LANCZOS)
d = ImageDraw.Draw(cr)
for i, (x, y) in P.items():
    if x0 <= x < x1 and y0 <= y < y1:
        px, py = (x - x0) * sc, (y - y0) * sc
        d.ellipse((px - 10, py - 10, px + 10, py + 10), outline=(255, 0, 0), width=2)
        d.text((px + 12, py - 24), f"#{i}", fill=(255, 0, 0), stroke_width=2, stroke_fill=(255, 255, 255))
cr.save(out, quality=92); print(out, cr.size, "area", int(x0), int(y0), int(x1), int(y1))
