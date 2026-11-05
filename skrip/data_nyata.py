"""Kumpulkan potongan berlabel dari s*_reads.json -> latih_nyata.npz (potongan tegak 64x64 abu-abu + nomor).

python data_nyata.py   (butuh s<peta>_cand.json dan s<peta>_reads.json di folder skrip)
Potongan: persegi +-R px di sekitar titik hitam, diputar supaya tegak sesuai pgw.
"""
import os, re, glob, json, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
R = 56; S = 96

def peta_dari_tag(tag):
    """s000102Inset1 -> '000102_Inset 1'"""
    m = re.match(r"s(\d{6})(?:_Inset(\d+))?$", tag)
    return m.group(1) + (f"_Inset {m.group(2)}" if m.group(2) else "") if m else None

def potong(im, cx, cy, rot):
    cr = im.crop((int(cx) - R, int(cy) - R, int(cx) + R, int(cy) + R))
    if rot: cr = cr.rotate(rot, expand=True)
    return np.asarray(cr.convert("L").resize((S, S), Image.LANCZOS), dtype=np.uint8)

def rotasi(pgw):
    A, D = [float(x) for x in open(pgw).read().split()[:2]]
    return (-90 if D < 0 else 90) if abs(D) > abs(A) else 0

if __name__ == "__main__":
    X, Y, T = [], [], []
    for f in sorted(glob.glob(os.path.join(SCR, "s*_reads.json"))):
        tag = os.path.basename(f)[:-len("_reads.json")]
        reads = json.load(open(f))
        if not reads: continue
        peta = peta_dari_tag(tag)
        desa = {"s000100": "005"}.get(tag, "004")      # tag berkas kerja dipakai bersama 004/005; yang dibaca user sejauh ini: 004 + 005/000100
        png = os.path.join(ROOT, "geo", desa, peta + "_WSS.png")
        if not os.path.exists(png): png = None
        if not png: print("tak ada png", tag); continue
        im = Image.open(png).convert("RGB"); rot = rotasi(png[:-4] + ".pgw")
        cand = {o["id"]: o for o in json.load(open(os.path.join(SCR, tag + "_cand.json")))}
        for k, v in reads.items():
            o = cand.get(int(k))
            if o and str(v).isdigit():
                X.append(potong(im, o["cx"], o["cy"], rot)); Y.append(str(int(v))); T.append(tag)
        print(tag, len(reads))
    # contoh tambahan dari user: D:\bot peta\contoh\<nomor>_<apa saja>.png/jpg = potongan satu nomor (titik + tulisan)
    for f in sorted(glob.glob(os.path.join(ROOT, "contoh", "*.*"))):
        nomor = os.path.basename(f).split("_")[0].split(".")[0]
        if not nomor.isdigit() or f.lower().rsplit(".", 1)[-1] not in ("png", "jpg", "jpeg"): continue
        g = Image.open(f).convert("L"); w, h = g.size; k = max(w, h)
        kv = Image.new("L", (k, k), int(np.median(np.asarray(g)))); kv.paste(g, ((k - w) // 2, (k - h) // 2))
        X.append(np.asarray(kv.resize((S, S), Image.LANCZOS), dtype=np.uint8)); Y.append(str(int(nomor))); T.append("contoh")
    np.savez(os.path.join(SCR, "latih_nyata.npz"), X=np.array(X), Y=np.array(Y), T=np.array(T))
    print("total", len(X))
