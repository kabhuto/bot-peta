"""Lembar pencarian untuk nomor merah: python merah.py <desa> <sls> <peta> [radius_m]

Untuk tiap nomor gpkg yang masih diparkir (belum_cocok) ditampilkan peta di sekitar posisi gpkg aslinya
(lingkaran merah), dengan id kandidat titik hitam bertulisan biru. Jawaban: s<peta>_reads.json
tambah {"<id kandidat>": nomor} untuk id yang tulisannya = nomor yang dicari.  Berkas: s<peta>_msheet*.jpg
"""
import os, sys, re, json, math, sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
desa, sls, peta = sys.argv[1:4]; RADM = float(sys.argv[4]) if len(sys.argv) > 4 else 45.0
tag = "s" + re.sub(r"\W", "", peta)
png = os.path.join(ROOT, "geo", desa, peta + "_WSS.png"); pgw = png[:-4] + ".pgw"
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
rot = 90 if abs(D) > abs(A) else 0
if rot and D < 0: rot = -90
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0; y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
c = sqlite3.connect(os.path.join(ROOT, desa, f"3526020{desa}{sls}_rapi_parkir.gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
rows = c.execute(f'select no_bang,lat_asli,lon_asli from "{t}" where status_pindah in ("parkir","belum_cocok")').fetchall()
lat0 = float(np.mean([r[1] for r in rows])); PS = math.hypot(A, D) * math.cos(math.radians(-lat0))
grp = {}
for nb, la, lo in rows: grp.setdefault(nb, []).append(to_px(la, lo))
cand = json.load(open(os.path.join(SCR, tag + "_cand.json")))
reads = json.load(open(os.path.join(SCR, tag + "_reads.json")))
im = Image.open(png).convert("RGB"); W, H = im.size
R = int(RADM / PS); S = 2 * R
font = ImageFont.truetype("arial.ttf", 20); fb = ImageFont.truetype("arialbd.ttf", 26); fs = ImageFont.truetype("arial.ttf", 17)
CELL = 500; COLS, ROWS = 3, 2
def tf(x, y):                                   # koordinat potongan -> koordinat setelah rotasi
    if rot == 90: return y, S - 1 - x
    if rot == -90: return S - 1 - y, x
    return x, y
items = sorted(grp.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0)
for s in range(math.ceil(len(items) / (COLS * ROWS))):
    sheet = Image.new("RGB", (CELL * COLS, CELL * ROWS), "white")
    for k, (nb, pts) in enumerate(items[s * COLS * ROWS:(s + 1) * COLS * ROWS]):
        p = np.mean(pts, axis=0); x0, y0 = int(p[0]) - R, int(p[1]) - R
        cr = im.crop((x0, y0, x0 + S, y0 + S))
        if rot: cr = cr.rotate(rot, expand=True)
        cr = cr.resize((CELL - 4, CELL - 4), Image.LANCZOS); sc = (CELL - 4) / S
        d = ImageDraw.Draw(cr)
        for o in cand:
            if x0 <= o["cx"] < x0 + S and y0 <= o["cy"] < y0 + S:
                u, v = tf(o["cx"] - x0, o["cy"] - y0)
                done = reads.get(str(o["id"]))
                d.text((u * sc + 6, v * sc - 22), str(o["id"]), fill=(0, 255, 255) if done else (0, 80, 255), font=fs)
        u, v = tf(R, R); u *= sc; v *= sc
        d.ellipse([u - 14, v - 14, u + 14, v + 14], outline=(255, 0, 0), width=3)
        for q in pts:
            if abs(q[0] - p[0]) < R and abs(q[1] - p[1]) < R:
                a, b = tf(q[0] - x0, q[1] - y0); a *= sc; b *= sc
                d.line([a - 7, b, a + 7, b], fill=(255, 0, 0), width=2); d.line([a, b - 7, a, b + 7], fill=(255, 0, 0), width=2)
        d.rectangle([0, 0, 170, 34], fill="white"); d.text((4, 2), f"CARI {nb}", fill=(200, 0, 0), font=fb)
        sheet.paste(cr, ((k % COLS) * CELL + 2, (k // COLS) * CELL + 2))
    sheet.save(os.path.join(SCR, f"{tag}_msheet{s}.jpg"), quality=88)
print(f"[{sls}] nomor merah: {len(items)}, lembar: {math.ceil(len(items) / (COLS * ROWS))}  radius {RADM} m")
