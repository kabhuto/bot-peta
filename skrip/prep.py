"""Siapkan satu SLS: python prep.py <desa> <sls> [RM_meter]

Langkah: salin gpkg ke folder kerja, ambil batas SLS dari garis merah, deteksi coretan tinta,
buat lembar potongan. Tiap potongan memuat nomor gpkg terdekat (kandidat) supaya pembacaan
tinggal memilih dari kandidat.  Berkas kerja ditulis di folder skrip dengan awalan s<sls>.
"""
import os, sys, re, math, json, shutil, sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\bot peta"
desa, sls = sys.argv[1:3]
RM = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
GROW = int(os.environ.get("GROW", 3)); MAXV = int(os.environ.get("MAXV", 85)); SAT = int(os.environ.get("SAT", 40))
GAP = int(os.environ.get("GAP", 24))
MAPNAME = os.environ.get("MAP", sls)          # contoh: "000102_Inset 1"
tag = "s" + re.sub(r"\W", "", MAPNAME)
png = os.path.join(ROOT, "geo", desa, MAPNAME + "_WSS.png"); pgw = png[:-4] + ".pgw"
src = os.path.join(ROOT, desa, "3526020" + desa + sls + ".gpkg")
shutil.copyfile(src, os.path.join(SCR, tag + ".gpkg"))
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
M = np.array([[A, B], [D, E]]); Minv = np.linalg.inv(M)
c = sqlite3.connect(os.path.join(SCR, tag + ".gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
rows = c.execute(f'select no_bang,geotag_latitude,geotag_longitude from "{t}"').fetchall()
lat0 = float(np.mean([r[1] for r in rows]))
PS = math.hypot(A, D) * math.cos(math.radians(-lat0))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
gp = np.array([to_px(r[1], r[2]) for r in rows]); nb = [r[0] for r in rows]
rot = 90 if abs(D) > abs(A) else 0
if rot and D < 0: rot = -90
imrgb = Image.open(png).convert("RGB"); arr = np.asarray(imrgb).astype(int)
H, W = arr.shape[:2]

# --- batas SLS dari garis merah
r_, g_, b_ = arr[..., 0], arr[..., 1], arr[..., 2]
red = (r_ > 170) & (g_ < 110) & (b_ < 130) & (r_ - g_ > 90)
if os.environ.get("LINE") == "warm":          # batas oranye/kuning (mis. peta 000103)
    red = (r_ > 190) & (b_ < 110) & (r_ - b_ > 120) & (g_ > 60)
free = ~ndi.binary_dilation(red, structure=np.ones((3, 3)), iterations=GAP)
lab, n = ndi.label(free)
cnt = {}
n_in = 0
for x, y in gp:
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < W and 0 <= yi < H:
        n_in += 1
        if lab[yi, xi] > 0:
            cnt[lab[yi, xi]] = cnt.get(lab[yi, xi], 0) + 1
if cnt and max(cnt.values()) >= 0.3 * max(1, n_in):
    best = max(cnt, key=cnt.get)
    inside = ndi.binary_dilation(lab == best, structure=np.ones((3, 3)), iterations=GAP)
else:                                         # peta inset tanpa batas SLS yang jelas: pakai seluruh bingkai peta
    inside = np.zeros((H, W), bool); mrg = int(0.04 * min(H, W)); inside[mrg:H - mrg, mrg:W - mrg] = True
    cnt = {1: n_in}; best = 1
frac = inside.sum() / float(H * W)
if frac > 0.6:                               # batas bocor: pakai kotak pembatas titik gpkg (diperlebar) sebagai area dalam
    inside = np.zeros((H, W), bool)
    xs_ = gp[:, 0][(gp[:, 0] > 0) & (gp[:, 0] < W)]; ys_ = gp[:, 1][(gp[:, 1] > 0) & (gp[:, 1] < H)]
    inside[max(0, int(ys_.min()) - 80):min(H, int(ys_.max()) + 80), max(0, int(xs_.min()) - 80):min(W, int(xs_.max()) + 80)] = True
    frac = inside.sum() / float(H * W); print("  (batas bocor -> pakai kotak pembatas titik)")
np.save(os.path.join(SCR, tag + "_inside.npy"), inside)
print(f"[{sls}] titik={len(rows)} m/px={PS:.3f} rotasi={rot} | batas SLS: memuat {cnt[best]} titik (di dalam gambar: {n_in}), luas {frac*100:.0f}% gambar"
      + ("  <-- PERIKSA (kemungkinan bocor)" if frac > 0.6 else ""))
vis = arr.copy().astype("uint8"); edge = inside & ~ndi.binary_erosion(inside, iterations=3); vis[edge] = [255, 255, 0]
Image.fromarray(vis).resize((W // 3, H // 3)).save(os.path.join(SCR, tag + "_boundary.jpg"), quality=85)

# --- deteksi titik hitam (posisi bangunan yang ditandai petugas)
ERO = int(os.environ.get("ERO", 2))
mx = arr.max(axis=2); mn = arr.min(axis=2)
mask = (mx < MAXV) & ((mx - mn) < SAT)
er = ndi.binary_erosion(mask, structure=np.ones((3, 3)), iterations=ERO)
lab2, n2 = ndi.label(er)
zone = ndi.binary_dilation(inside, iterations=int(40 / PS))
cand = []
for i, sl_ in enumerate(ndi.find_objects(lab2), 1):
    h = sl_[0].stop - sl_[0].start; w = sl_[1].stop - sl_[1].start
    if max(h, w) > 26 or min(h, w) < 4 or max(h, w) / max(1, min(h, w)) > 2.2: continue
    cy, cx = ndi.center_of_mass(lab2 == i)
    if not zone[int(cy), int(cx)]: continue
    if np.hypot(gp[:, 0] - cx, gp[:, 1] - cy).min() * PS > RM: continue
    if any(np.hypot(d_["cx"] - cx, d_["cy"] - cy) < 16 for d_ in cand): continue
    cand.append(dict(id=len(cand), cx=float(cx), cy=float(cy)))
json.dump(cand, open(os.path.join(SCR, tag + "_cand.json"), "w"))
print(f"[{sls}] titik hitam kandidat: {len(cand)} | titik gpkg: {len(rows)} | nomor unik gpkg: {len({r[0] for r in rows})}")

# --- lembar potongan: area di bawah titik (arah bawah tegak = x menurun), lingkaran merah = titik yang dimaksud
font = ImageFont.truetype("arial.ttf", 19); fsm = ImageFont.truetype("arial.ttf", 15)
BELOW, ABOVE, HALF = 78, 16, 33
CW, CH, COLS, ROWS = 250, 385, 6, 3; PER = COLS * ROWS
AROUND = int(os.environ.get("AROUND", 0))     # >0: potongan persegi di sekeliling titik (angka di atas/samping titik)
if AROUND:
    BELOW = ABOVE = HALF = AROUND; CW, CH, COLS, ROWS = 300, 360, 5, 3; PER = COLS * ROWS
for s in range(math.ceil(len(cand) / PER)):
    sheet = Image.new("RGB", (CW * COLS, CH * ROWS), "white"); dr = ImageDraw.Draw(sheet)
    for k, o in enumerate(cand[s * PER:(s + 1) * PER]):
        cx_, cy_ = int(o["cx"]), int(o["cy"])
        if AROUND:
            box = (cx_ - AROUND, cy_ - AROUND, cx_ + AROUND, cy_ + AROUND); mark = (AROUND, AROUND)
        elif rot == 90:      # "bawah" tegak = x mengecil
            box = (cx_ - BELOW, cy_ - HALF, cx_ + ABOVE, cy_ + HALF); mark = (BELOW, HALF)
        elif rot == -90:   # "bawah" tegak = x membesar
            box = (cx_ - ABOVE, cy_ - HALF, cx_ + BELOW, cy_ + HALF); mark = (ABOVE, HALF)
        else:              # tidak berotasi: "bawah" = y membesar
            box = (cx_ - HALF, cy_ - ABOVE, cx_ + HALF, cy_ + BELOW); mark = (HALF, ABOVE)
        cr = imrgb.crop(box)
        ImageDraw.Draw(cr).ellipse([mark[0] - 11, mark[1] - 11, mark[0] + 11, mark[1] + 11], outline=(255, 0, 0), width=2)
        if rot: cr = cr.rotate(rot, expand=True)
        cr = cr.resize((int(cr.width * 3.6), int(cr.height * 3.6)), Image.LANCZOS); cr.thumbnail((CW - 6, CH - 62))
        x = (k % COLS) * CW; y = (k // COLS) * CH
        sheet.paste(cr, (x + 3, y + 24)); dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline="gray")
        d = np.hypot(gp[:, 0] - o["cx"], gp[:, 1] - o["cy"]) * PS
        seen = []
        for j in np.argsort(d):
            if d[j] > RM: break
            v = str(int(nb[j])) if nb[j] and nb[j].isdigit() else str(nb[j])
            if v not in seen: seen.append(v)
            if len(seen) >= 8: break
        dr.text((x + 5, y + 2), f"#{o['id']}", fill="red", font=font)
        dr.text((x + 5, y + CH - 38), "kand: " + ",".join(seen[:4]), fill=(0, 90, 200), font=fsm)
        dr.text((x + 5, y + CH - 20), (",".join(seen[4:8]) if len(seen) > 4 else ""), fill=(0, 90, 200), font=fsm)
    sheet.save(os.path.join(SCR, f"{tag}_sheet{s}.jpg"), quality=88)
print(f"[{sls}] lembar: {math.ceil(len(cand) / PER)}  (berkas: {tag}_sheet*.jpg)")
