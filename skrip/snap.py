"""Tempelkan kandidat 'tulisan' ke titik hitam terdekat: python snap.py <desa> <peta> [radius_px]

Kandidat yang dibuat dari gumpalan tulisan (kind=tulisan) berada di pusat angka. Bila ada titik hitam kecil
dalam radius, posisinya dipindah ke titik itu (posisi sebenarnya bangunan). Berkas s<peta>_cand.json diperbarui.
"""
import os, sys, re, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
desa, peta = sys.argv[1:3]; RAD = float(sys.argv[3]) if len(sys.argv) > 3 else 45
tag = "s" + re.sub(r"\W", "", peta)
arr = np.asarray(Image.open(os.path.join(ROOT, "geo", desa, peta + "_WSS.png")).convert("RGB")).astype(int)
mx = arr.max(axis=2); mn = arr.min(axis=2)
mask = (mx < 80) & ((mx - mn) < 40)
er = ndi.binary_erosion(mask, structure=np.ones((3, 3)), iterations=1)
lab, n = ndi.label(er)
dots = []
for i, sl in enumerate(ndi.find_objects(lab), 1):
    h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
    if 4 <= min(h, w) and max(h, w) <= 26 and max(h, w) / max(1, min(h, w)) <= 2.2:
        cy, cx = ndi.center_of_mass(lab == i); dots.append((cx, cy))
dots = np.array(dots)
cand = json.load(open(os.path.join(SCR, tag + "_cand.json"))); k = 0
for o in cand:
    if o.get("kind") != "tulisan" or o.get("snap"): continue
    d = np.hypot(dots[:, 0] - o["cx"], dots[:, 1] - o["cy"]); j = int(np.argmin(d))
    if d[j] <= RAD:
        o["cx"], o["cy"] = float(dots[j][0]), float(dots[j][1]); o["snap"] = True; k += 1
json.dump(cand, open(os.path.join(SCR, tag + "_cand.json"), "w"))
print(f"{tag}: {k} kandidat tulisan menempel ke titik hitam")
