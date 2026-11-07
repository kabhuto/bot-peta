r"""Tampilan luas untuk pembacaan: python luas.py <desa> <peta> [lebar] [tinggi] [skala]

Peta diputar tegak (sama seperti lembar potongan), lalu dipotong jadi ubin lebar dengan id kandidat
tertulis di sebelah tiap lingkaran. Id yang sudah punya bacaan ditulis hijau beserta nomornya,
id yang belum ditulis merah. Keluaran: luas_<tag>_<n>.jpg di folder skrip. Hanya untuk dibaca; tidak mengubah apa pun.
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SCR)
from tagutil import tag_for
desa, mapname = sys.argv[1:3]
TW = int(sys.argv[3]) if len(sys.argv) > 3 else 800; TH = int(sys.argv[4]) if len(sys.argv) > 4 else 600
SC = float(sys.argv[5]) if len(sys.argv) > 5 else 1.6
tag = tag_for(desa, mapname)
png = os.path.join(r"D:\bot peta", "geo", desa, mapname + "_WSS.png"); pgw = png[:-4] + ".pgw"
A, D = [float(x) for x in open(pgw).read().split()[:2]]
rot = 90 if abs(D) > abs(A) else 0
if rot and D < 0: rot = -90
cand = json.load(open(os.path.join(SCR, tag + "_cand.json")))
rp = os.path.join(SCR, tag + "_reads.json"); reads = json.load(open(rp)) if os.path.exists(rp) else {}
im = Image.open(png).convert("RGB"); W, H = im.size
if rot: im = im.rotate(rot, expand=True)
def tr(x, y):
    if rot == -90: return H - 1 - y, x
    if rot == 90: return y, W - 1 - x
    return x, y
pts = [(c["id"],) + tr(c["cx"], c["cy"]) for c in cand]
xs = [p[1] for p in pts]; ys = [p[2] for p in pts]; pad = 120
x0, x1, y0, y1 = max(0, int(min(xs)) - pad), min(im.width, int(max(xs)) + pad), max(0, int(min(ys)) - pad), min(im.height, int(max(ys)) + pad)
font = ImageFont.truetype("arialbd.ttf", 15) if os.path.exists(r"C:\Windows\Fonts\arialbd.ttf") else ImageFont.load_default()
n = 0; step_x = TW - 60; step_y = TH - 60
for ty in range(y0, y1, step_y):
    for tx in range(x0, x1, step_x):
        box = (tx, ty, min(tx + TW, im.width), min(ty + TH, im.height))
        inside = [p for p in pts if box[0] + 15 <= p[1] < box[2] - 15 and box[1] + 15 <= p[2] < box[3] - 15]
        if not inside: continue
        cr = im.crop(box).resize((int((box[2] - box[0]) * SC), int((box[3] - box[1]) * SC)), Image.LANCZOS)
        d = ImageDraw.Draw(cr)
        for i, x, y in inside:
            px, py = (x - box[0]) * SC, (y - box[1]) * SC
            v = reads.get(str(i)); col = (0, 200, 0) if v is not None else (255, 0, 0)
            d.ellipse((px - 9, py - 9, px + 9, py + 9), outline=col, width=2)
            d.text((px + 11, py - 22), f"#{i}" + (f"={v}" if v is not None else ""), fill=col, font=font, stroke_width=2, stroke_fill=(255, 255, 255))
        fn = os.path.join(SCR, f"luas_{tag}_{n}.jpg"); cr.save(fn, quality=88); print(fn, len(inside), "box", box, "skala", SC); n += 1
