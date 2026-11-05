import sys, os, json, math, sqlite3
import numpy as np
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
png, pgw, tag = sys.argv[1:4]
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
c = sqlite3.connect(os.path.join(SCR, tag + ".gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
gp = np.array([to_px(la, lo) for la, lo in c.execute(f'select geotag_latitude,geotag_longitude from "{t}"')])
cand = json.load(open(os.path.join(SCR, tag + "_ink.json")))
keep = []
for o in cand:
    d = np.hypot(gp[:, 0] - o["cx"], gp[:, 1] - o["cy"]).min()
    if d < float(os.environ.get("DMAX", 160)):
        o["dgp"] = float(d); keep.append(o)
print("kandidat dekat titik gpkg:", len(keep), "dari", len(cand))
json.dump(keep, open(os.path.join(SCR, tag + "_cand.json"), "w"))
im = Image.open(png).convert("RGB")
font = ImageFont.truetype("arial.ttf", 22)
S = 4; PAD = 14; CW, CH = 200, 210; COLS = 6; ROWS = 5; PER = COLS * ROWS
for s in range(math.ceil(len(keep) / PER)):
    sheet = Image.new("RGB", (CW * COLS, CH * ROWS), "white")
    dr = ImageDraw.Draw(sheet)
    for k, o in enumerate(keep[s * PER:(s + 1) * PER]):
        cr = im.crop((o["x0"] - PAD, o["y0"] - PAD, o["x1"] + PAD, o["y1"] + PAD)).rotate(90, expand=True)
        cr = cr.resize((cr.width * S, cr.height * S), Image.LANCZOS)
        cr.thumbnail((CW - 6, CH - 34))
        x = (k % COLS) * CW; y = (k // COLS) * CH
        sheet.paste(cr, (x + 3, y + 30))
        dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline="gray")
        dr.text((x + 6, y + 3), f"#{o['id']}", fill="red", font=font)
    sheet.save(os.path.join(SCR, f"{tag}_sheet{s}.jpg"), quality=90)
print("lembar:", math.ceil(len(keep) / PER))
