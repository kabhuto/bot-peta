r"""Tambah kandidat manual (titik hitam yang tidak terdeteksi, atau tulisan tanpa titik) lengkap dengan bacaannya.

  python tambah.py <desa> <peta> <boxx> <boxy> <skala> <px,py,nomor> [<px,py,nomor> ...]

<boxx> <boxy> <skala> diambil dari keluaran luas.py ("box (x0, y0, ...) skala 1.8"); px,py = posisi di gambar ubin.
Nomor boleh diberi '?' di belakangnya (ragu -> kuning). Id baru = id terbesar + 1; id lama tidak berubah.
Berkas: s<tag>_cand.json dan s<tag>_reads.json (tidak ada yang ditimpa selain dua berkas itu).
"""
import os, sys, json
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SCR)
from tagutil import tag_for
desa, mapname, bx, by, sc = sys.argv[1:6]; bx, by, sc = float(bx), float(by), float(sc)
tag = tag_for(desa, mapname)
png = os.path.join(r"D:\bot peta", "geo", desa, mapname + "_WSS.png")
A, D = [float(x) for x in open(png[:-4] + ".pgw").read().split()[:2]]
rot = 90 if abs(D) > abs(A) else 0
if rot and D < 0: rot = -90
W, H = Image.open(png).size
def inv(x, y):                      # koordinat peta tegak -> piksel png asli
    if rot == -90: return y, H - 1 - x
    if rot == 90: return W - 1 - y, x
    return x, y
cp, rp = os.path.join(SCR, tag + "_cand.json"), os.path.join(SCR, tag + "_reads.json")
cand = json.load(open(cp)); reads = json.load(open(rp)) if os.path.exists(rp) else {}
for t in sys.argv[6:]:
    px, py, nomor = t.split(",")
    cx, cy = inv(bx + float(px) / sc, by + float(py) / sc); nid = max([k["id"] for k in cand] + [-1]) + 1
    cand.append(dict(id=nid, cx=float(cx), cy=float(cy), kind="manual"))
    reads[str(nid)] = int(nomor) if nomor.isdigit() else nomor
    print("id", nid, "=", nomor)
json.dump(cand, open(cp, "w")); json.dump(reads, open(rp, "w"))
