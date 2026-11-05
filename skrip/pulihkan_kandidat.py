"""Bangun ulang s<peta>_cand.json peta utama dari berkas hasil: python pulihkan_kandidat.py <desa> <sls> <peta> <berkas_hasil> <indeks_peta>

Kolom blob_id di berkas hasil = indeks_peta*10000 + id kandidat; posisi kandidat = geometri titik. Hanya id yang
dipakai hasil yang bisa dipulihkan; id lain diisi posisi di luar gambar supaya bacaannya tidak cocok ke mana pun.
"""
import os, sys, re, json, math, sqlite3, struct
import numpy as np
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
sys.path.insert(0, SCR)
from tagutil import tag_for
desa, sls, peta, hasil, ip = sys.argv[1:6]; ip = int(ip)
tag = tag_for(desa, peta)
pgw = os.path.join(ROOT, "geo", desa, peta + "_WSS.pgw")
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
c = sqlite3.connect(hasil); T = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
pos = {}
for bid, g in c.execute(f'select blob_id,geom from "{T}" where blob_id is not null'):
    if ip * 10000 <= bid < (ip + 1) * 10000:
        lon, lat = struct.unpack("<dd", g[13:29])
        x = lon * 6378137.0 * math.pi / 180.0; y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        u, v = Minv @ np.array([x - C, y - F]); pos[bid - ip * 10000] = (float(u), float(v))
reads = json.load(open(os.path.join(SCR, tag + "_reads.json")))
n = max([int(k) for k in reads] + list(pos)) + 1
cand = [dict(id=i, cx=pos[i][0] if i in pos else -99999.0, cy=pos[i][1] if i in pos else -99999.0) for i in range(n)]
json.dump(cand, open(os.path.join(SCR, tag + "_cand.json"), "w"))
print(f"{tag}: {len(pos)} kandidat dipulihkan dari hasil, {n - len(pos)} id tidak terpulihkan (diberi posisi di luar gambar)")
