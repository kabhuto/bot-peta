import sys, os, json, math, sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
png, pgw, tag, draft = sys.argv[1:5]
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
imrgb = Image.open(png).convert("RGB")
im = np.asarray(imrgb).astype(float)
gray = im.mean(axis=2); chroma = im.max(axis=2) - im.min(axis=2)
bg = ndi.gaussian_filter(gray, 14)
CON = float(os.environ.get("CON", 34)); GMAX = float(os.environ.get("GMAX", 125))
ink = ((bg - gray) > CON) & (gray < GMAX) & (chroma < 75)
if os.environ.get("STRICT"):
    ink = (im.max(axis=2) < float(os.environ["STRICT"])) & (chroma < 35)
er = ndi.binary_erosion(ink, structure=np.ones((3, 3)), iterations=int(os.environ.get("ERO", 2)))
lab, n = ndi.label(er)

inside = np.load(os.path.join(SCR, tag + "_inside.npy"))
near_zone = ndi.binary_dilation(inside, iterations=int(os.environ.get("ZONE", 150)))
old = json.load(open(os.path.join(SCR, tag + "_dots.json")))
dots = [dict(src="lama", **{k: o[k] for k in ("cx", "cy")}) for o in old]
new = 0
for i, sl in enumerate(ndi.find_objects(lab), 1):
    h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
    if max(h, w) > 28 or min(h, w) < int(os.environ.get("MINW", 3)) or max(h, w) / max(1, min(h, w)) > 2.0:
        continue
    cy, cx = ndi.center_of_mass(lab == i)
    if not near_zone[int(cy), int(cx)]:
        continue
    if any(np.hypot(d["cx"] - cx, d["cy"] - cy) < 18 for d in dots):
        continue
    dots.append(dict(src="baru", cx=float(cx), cy=float(cy))); new += 1
print("titik lama:", len(old), "| titik baru dari deteksi kontras:", new)

# titik tulisan yang sudah dipakai oleh titik gpkg yang dipindah
c = sqlite3.connect(draft)
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
used = [o for o in old if o["id"] in {r[0] for r in c.execute(f'select blob_id from "{t}" where blob_id is not null')}]
parked = sorted(r[0] for r in c.execute(f'select no_bang from "{t}" where status_pindah=?', ("belum_cocok",)))
park_px = np.array([to_px(la, lo) for la, lo in c.execute(f'select geotag_latitude,geotag_longitude from "{t}" where status_pindah=?', ("belum_cocok",))])
print("titik gpkg belum cocok:", len(parked), parked)
U = []
for d in dots:
    if any(np.hypot(u["cx"] - d["cx"], u["cy"] - d["cy"]) < 18 for u in used):
        continue
    d["id"] = len(U); U.append(d)
print("titik tulisan belum terpakai:", len(U))
json.dump(U, open(os.path.join(SCR, tag + "_unused.json"), "w"))

W0, H0 = 105, 38
font = ImageFont.truetype("arial.ttf", 22)
CW, CH, COLS, ROWS = 200, 210, 6, 5
PER = COLS * ROWS
for s in range(math.ceil(len(U) / PER)):
    sheet = Image.new("RGB", (CW * COLS, CH * ROWS), "white"); dr = ImageDraw.Draw(sheet)
    for k, o in enumerate(U[s * PER:(s + 1) * PER]):
        box = (int(o["cx"] - W0), int(o["cy"] - H0), int(o["cx"] + 25), int(o["cy"] + H0))
        cr = imrgb.crop(box)
        ImageDraw.Draw(cr).ellipse([W0 - 13, H0 - 13, W0 + 13, H0 + 13], outline=(255, 0, 0), width=2)
        cr = cr.rotate(90, expand=True)
        cr = cr.resize((cr.width * 3, cr.height * 3), Image.LANCZOS); cr.thumbnail((CW - 6, CH - 34))
        x = (k % COLS) * CW; y = (k // COLS) * CH
        sheet.paste(cr, (x + 3, y + 30)); dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline="gray")
        dr.text((x + 6, y + 3), f"#{o['id']}{'*' if o['src']=='baru' else ''}", fill="red", font=font)
    sheet.save(os.path.join(SCR, f"{tag}_usheet{s}.jpg"), quality=90)
print("lembar:", math.ceil(len(U) / PER))
