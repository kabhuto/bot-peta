import sys, os, math, sqlite3, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
png, pgw, tag = sys.argv[1:4]
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
im = np.asarray(Image.open(png).convert("RGB")).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
red = (r > 170) & (g < 110) & (b < 130) & (r - g > 90)
print("piksel merah:", red.sum())
GAP = int(os.environ.get("GAP", 9))
closed = ndi.binary_dilation(red, structure=np.ones((3, 3)), iterations=GAP)
free = ~closed
lab, n = ndi.label(free)
c = sqlite3.connect(os.path.join(SCR, tag + ".gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
pts = np.array([to_px(la, lo) for la, lo in c.execute(f'select geotag_latitude,geotag_longitude from "{t}"')])
# komponen yang paling banyak memuat titik gpkg
H, W = lab.shape
cnt = {}
for x, y in pts:
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < W and 0 <= yi < H and lab[yi, xi] > 0:
        cnt[lab[yi, xi]] = cnt.get(lab[yi, xi], 0) + 1
print("komponen berisi titik:", sorted(cnt.items(), key=lambda kv: -kv[1])[:5], "dari", len(pts))
best = max(cnt, key=cnt.get)
inside = lab == best
inside = ndi.binary_dilation(inside, structure=np.ones((3, 3)), iterations=GAP)  # kembalikan lebar garis
print("luas dalam SLS (px):", int(inside.sum()), "= %.1f ha" % (inside.sum() * 0.2853 ** 2 / 10000))
np.save(os.path.join(SCR, tag + "_inside.npy"), inside)
vis = im.copy().astype("uint8")
edge = inside & ~ndi.binary_erosion(inside, iterations=3)
vis[edge] = [255, 255, 0]
Image.fromarray(vis).resize((W // 2, H // 2)).save(os.path.join(SCR, tag + "_boundary.jpg"), quality=88)
