import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
png, tag = sys.argv[1:3]
im = np.asarray(Image.open(png).convert("RGB")).astype(int)
mx = im.max(axis=2); mn = im.min(axis=2)
# tinta hitam: sangat gelap & hampir tanpa warna
mask = (mx < int(os.environ.get("MAXV", 80))) & ((mx - mn) < int(os.environ.get("SAT", 40)))
# buang bagian luar bingkai peta (kolom legenda dsb) ditangani belakangan lewat bbox titik gpkg
print("piksel tinta:", mask.sum())
# gabungkan coretan satu angka (digit berdekatan)
grow = ndi.binary_dilation(mask, structure=np.ones((3, 3)), iterations=int(os.environ.get("GROW", 7)))
lab, n = ndi.label(grow)
print("komponen:", n)
objs = ndi.find_objects(lab)
out = []
for i, sl in enumerate(objs, 1):
    ys, xs = sl
    h = ys.stop - ys.start; w = xs.stop - xs.start
    ink = int(mask[sl][lab[sl] == i].sum())
    if ink < 25 or max(h, w) > 140:
        continue
    yy, xx = np.nonzero(mask[sl] & (lab[sl] == i))
    out.append(dict(id=len(out), cx=float(xx.mean() + xs.start), cy=float(yy.mean() + ys.start),
                    x0=xs.start, y0=ys.start, x1=xs.stop, y1=ys.stop, ink=ink))
print("kandidat angka:", len(out))
json.dump(out, open(os.path.join(SCR, tag + "_ink.json"), "w"))
vis = Image.fromarray(np.where(mask[..., None], np.array([255, 0, 255]), im).astype("uint8"))
vis.save(os.path.join(SCR, tag + "_mask.png"))
