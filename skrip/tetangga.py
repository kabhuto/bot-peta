"""Cari nomor merah lewat tetangganya: python tetangga.py <desa> <sls> "<peta>" [radius_m] [mulai]

Nomor di peta WSS berurutan menyusuri jalan, jadi nomor n yang belum ketemu biasanya dekat n-1 / n+1 yang sudah ketemu.
Untuk tiap nomor yang masih diparkir: potongan peta di sekitar tetangga yang sudah ditempatkan (kotak hijau + nomornya),
dengan SEMUA titik hitam diberi id (id baru ditambahkan ke s<peta>_cand.json, id lama tidak berubah).
Jawab dengan: s<peta>_reads.json += {"<id>": nomor}.  Berkas: s<peta>_tsheet*.jpg
"""
import os, sys, re, json, math, sqlite3, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
desa, sls, peta = sys.argv[1:4]; RADM = float(sys.argv[4]) if len(sys.argv) > 4 else 22.0
tag = "s" + re.sub(r"\W", "", peta)
png = os.path.join(ROOT, "geo", desa, peta + "_WSS.png")
A, D, B, E, C, F = [float(x) for x in open(png[:-4] + ".pgw").read().split()]
M = np.array([[A, B], [D, E]]); Minv = np.linalg.inv(M)
rot = 90 if abs(D) > abs(A) else 0
if rot and D < 0: rot = -90
def to_px(lon, lat):
    x = lon * 6378137.0 * math.pi / 180.0; y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
c = sqlite3.connect(os.path.join(ROOT, desa, f"3526020{desa}{sls}_rapi_parkir.gpkg"))
T = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
found, red = {}, set()
lat0 = None
for nb, g, st, la in c.execute(f'select no_bang,geom,status_pindah,lat_asli from "{T}"'):
    if not (nb and str(nb).isdigit()): continue
    n = int(nb); lat0 = la if lat0 is None else lat0
    if st in ("dipindah", "dipindah_cek"):
        lon, lat = struct.unpack("<dd", g[13:29]); found[n] = to_px(lon, lat)
    else: red.add(n)
PS = math.hypot(A, D) * math.cos(math.radians(-lat0))
im = Image.open(png).convert("RGB"); W, H = im.size
arr = np.asarray(im).astype(int); mx = arr.max(axis=2); mn = arr.min(axis=2)
er = ndi.binary_erosion((mx < 80) & ((mx - mn) < 40), structure=np.ones((3, 3)), iterations=1)
lab, nl = ndi.label(er); dots = []
for i, sl_ in enumerate(ndi.find_objects(lab), 1):
    h = sl_[0].stop - sl_[0].start; w = sl_[1].stop - sl_[1].start
    if 4 <= min(h, w) and max(h, w) <= 30 and max(h, w) / max(1, min(h, w)) <= 2.4:
        cy, cx = ndi.center_of_mass(lab == i); dots.append((cx, cy))
cand = json.load(open(os.path.join(SCR, tag + "_cand.json"))); reads = json.load(open(os.path.join(SCR, tag + "_reads.json")))
R = int(RADM / PS); S = 2 * R
def tf(x, y):
    if rot == 90: return y, S - 1 - x
    if rot == -90: return S - 1 - y, x
    return x, y
font = ImageFont.truetype("arial.ttf", 17); fb = ImageFont.truetype("arialbd.ttf", 26); fg = ImageFont.truetype("arialbd.ttf", 16)
CELL = 500; COLS, ROWS = 3, 2; items = []
for n in sorted(red):
    nb_ = [(abs(k - n), k) for k in found if abs(k - n) <= 3]
    if not nb_: continue
    nb_.sort(); use = [k for _, k in nb_[:2]]
    ctr = np.mean([found[k] for k in use], axis=0); items.append((n, ctr, use))
newc = 0
for s in range(math.ceil(len(items) / (COLS * ROWS))):
    sheet = Image.new("RGB", (CELL * COLS, CELL * ROWS), "white")
    for k, (n, ctr, use) in enumerate(items[s * COLS * ROWS:(s + 1) * COLS * ROWS]):
        x0, y0 = int(ctr[0]) - R, int(ctr[1]) - R
        for dx, dy in dots:
            if x0 <= dx < x0 + S and y0 <= dy < y0 + S and not any(math.hypot(o["cx"] - dx, o["cy"] - dy) < 14 for o in cand):
                cand.append(dict(id=len(cand), cx=float(dx), cy=float(dy), kind="titik")); newc += 1
        cr = im.crop((x0, y0, x0 + S, y0 + S))
        if rot: cr = cr.rotate(rot, expand=True)
        cr = cr.resize((CELL - 4, CELL - 4), Image.LANCZOS); sc = (CELL - 4) / S; d = ImageDraw.Draw(cr)
        for o in cand:
            if x0 <= o["cx"] < x0 + S and y0 <= o["cy"] < y0 + S:
                u, v = tf(o["cx"] - x0, o["cy"] - y0); done = reads.get(str(o["id"]))
                d.text((u * sc + 5, v * sc - 20), str(o["id"]), fill=(0, 255, 255) if done else (0, 70, 255), font=font)
        for kk in use:
            u, v = tf(found[kk][0] - x0, found[kk][1] - y0); u *= sc; v *= sc
            d.rectangle([u - 8, v - 8, u + 8, v + 8], outline=(0, 200, 0), width=3); d.text((u + 9, v + 4), f"={kk}", fill=(0, 200, 0), font=fg)
        d.rectangle([0, 0, 190, 34], fill="white"); d.text((4, 2), f"CARI {n}", fill=(200, 0, 0), font=fb)
        sheet.paste(cr, ((k % COLS) * CELL + 2, (k // COLS) * CELL + 2))
    sheet.save(os.path.join(SCR, f"{tag}_tsheet{s}.jpg"), quality=88)
json.dump(cand, open(os.path.join(SCR, tag + "_cand.json"), "w"))
print(f"[{sls}] nomor merah: {len(red)}, dengan tetangga: {len(items)}, lembar: {math.ceil(len(items) / (COLS * ROWS))}, kandidat baru: {newc} (radius {RADM} m)")
