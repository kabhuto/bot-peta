import sys, os, json, math, sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
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
imrgb = Image.open(png).convert("RGB")
im = np.asarray(imrgb).astype(int)
mx = im.max(axis=2); mn = im.min(axis=2)
mask = (mx < int(os.environ.get("MAXV", 85))) & ((mx - mn) < int(os.environ.get("SAT", 40)))
er = ndi.binary_erosion(mask, structure=np.ones((3, 3)), iterations=int(os.environ.get("ERO", 4)))
lab, n = ndi.label(er)
c = sqlite3.connect(os.path.join(SCR, tag + ".gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
gp = np.array([to_px(la, lo) for la, lo in c.execute(f'select geotag_latitude,geotag_longitude from "{t}"')])
dmax = float(os.environ.get("DMAX", 400))
dots = []
for i, sl in enumerate(ndi.find_objects(lab), 1):
    h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
    if max(h, w) > 26 or min(h, w) < 4 or max(h, w) / max(1, min(h, w)) > 2.2:
        continue
    cy, cx = ndi.center_of_mass(lab == i)
    if np.hypot(gp[:, 0] - cx, gp[:, 1] - cy).min() > dmax:
        continue
    if any(np.hypot(d_["cx"] - cx, d_["cy"] - cy) < 16 for d_ in dots):
        continue
    dots.append(dict(id=len(dots), cx=float(cx), cy=float(cy)))
print("titik hitam terdeteksi:", len(dots), "| titik gpkg:", len(gp))
json.dump(dots, open(os.path.join(SCR, tag + "_dots.json"), "w"))
# potongan: area di bawah titik (dalam orientasi tegak = x menurun pada gambar asli)
W0, H0 = 105, 38   # panjang ke "bawah", setengah lebar
font = ImageFont.truetype("arial.ttf", 22)
CW, CH, COLS, ROWS = 200, 210, 6, 5
PER = COLS * ROWS
for s in range(math.ceil(len(dots) / PER)):
    sheet = Image.new("RGB", (CW * COLS, CH * ROWS), "white"); dr = ImageDraw.Draw(sheet)
    for k, o in enumerate(dots[s * PER:(s + 1) * PER]):
        box = (int(o["cx"] - W0), int(o["cy"] - H0), int(o["cx"] + 25), int(o["cy"] + H0))
        cr = imrgb.crop(box)
        ImageDraw.Draw(cr).ellipse([W0 - 13, H0 - 13, W0 + 13, H0 + 13], outline=(255, 0, 0), width=2)
        cr = cr.rotate(90, expand=True)
        cr = cr.resize((cr.width * 3, cr.height * 3), Image.LANCZOS); cr.thumbnail((CW - 6, CH - 34))
        x = (k % COLS) * CW; y = (k // COLS) * CH
        sheet.paste(cr, (x + 3, y + 30)); dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline="gray")
        dr.text((x + 6, y + 3), f"#{o['id']}", fill="red", font=font)
    sheet.save(os.path.join(SCR, f"{tag}_dsheet{s}.jpg"), quality=90)
print("lembar:", math.ceil(len(dots) / PER))
