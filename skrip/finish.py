r"""Selesaikan satu SLS (boleh banyak peta: inset dulu, peta utama terakhir).

  python finish.py <desa> <sls> "<peta1>,<peta2>,..." [RM_meter]
  contoh: python finish.py 004 000102 "000102_Inset 1,000102" 400

Tiap peta butuh s<nama>_cand.json dan s<nama>_reads.json (hasil prep.py + pembacaan manual).
Aturan: titik gpkg bernomor sama ditumpuk di SATU tulisan tangan, memakai peta yang lebih dulu di daftar
menemukannya. Yang tidak ditemukan di peta mana pun diparkir di luar batas SLS (batas dari peta terakhir).
Hasil disimpan di <akar>\<desa>\<kode>_rapi_parkir.gpkg lalu rekap Excel diperbarui.
"""
import os, sys, re, shutil, sqlite3, subprocess, collections
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
desa, sls, maps = sys.argv[1:4]; RM = sys.argv[4] if len(sys.argv) > 4 else "400"
maps = [m.strip() for m in maps.split(",")]
kode = "3526020" + desa + sls
sys.path.insert(0, SCR)
from tagutil import tag_for
tags = [tag_for(desa, m) for m in maps]
envb = dict(os.environ, RM=RM, PYTHONIOENCODING="utf-8")
drafts = []
for m, tg in zip(maps, tags):
    png = os.path.join(ROOT, "geo", desa, m + "_WSS.png"); pgw = png[:-4] + ".pgw"
    dr = os.path.join(SCR, tg + "_draft.gpkg")
    r = subprocess.run([sys.executable, os.path.join(SCR, "match.py"), pgw, tg, dr], env=envb, capture_output=True, text=True)
    print(f"== {m}"); print("\n".join(l for l in r.stdout.splitlines() if "nomor gpkg terdekat" not in l))
    if r.returncode: print(r.stderr[-500:])
    drafts.append(dr)

# gabung per kelompok nomor: peta pertama yang menemukan kelompok itu menang
conns = [sqlite3.connect(d) for d in drafts]
T = conns[0].execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
data = []
for c in conns:
    data.append({r[0]: r[1:] for r in c.execute(f'select fid,no_bang,status_pindah,geom,jarak_pindah_m,blob_id,lat_asli,lon_asli from "{T}"')})
fids = sorted(data[0]); groups = collections.defaultdict(list)
for f in fids: groups[data[0][f][0]].append(f)
final = os.path.join(SCR, tags[-1] + "_final_gab.gpkg"); shutil.copyfile(drafts[-1], final)
cf = sqlite3.connect(final); chosen = {}
import struct, math
import numpy as np

def footprint(m):
    """kotak piksel inset -> fungsi (lon,lat) -> di dalam gambar? (peta utama tidak dipakai untuk menimpa area inset)"""
    pgw = os.path.join(ROOT, "geo", desa, m + "_WSS.pgw")
    A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
    Wm, Hm = Image.open(os.path.join(ROOT, "geo", desa, m + "_WSS.png")).size
    Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
    def inside_(lon, lat):
        x = lon * 6378137.0 * math.pi / 180.0; y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
        u, v = Minv @ np.array([x - C, y - F]); return 0 <= u < Wm and 0 <= v < Hm
    return inside_
insets = [footprint(m) for m in maps[:-1]] if os.environ.get("MAIN_DALAM_INSET") != "1" else []
dropped = []
for nb, fl in groups.items():
    for k, d in enumerate(data):
        if any(d[f][1] in ("dipindah", "dipindah_cek") for f in fl):
            if k == len(data) - 1 and insets:                  # hasil peta utama di dalam area inset: tidak dipercaya
                lon, lat = struct.unpack("<dd", d[fl[0]][2][13:29])
                if any(ins(lon, lat) for ins in insets):
                    dropped.append(nb); break
            chosen[nb] = k; break
if dropped: print(f"nomor hasil peta utama di dalam area inset (tidak dipakai, diparkir): {len(dropped)} -> {sorted(dropped, key=lambda s: int(s))}")
for nb, fl in groups.items():
    k = chosen.get(nb)
    for f in fl:
        if k is None:
            cf.execute(f'update "{T}" set status_pindah=?, jarak_pindah_m=NULL, blob_id=NULL where fid=?', ("belum_cocok", f)); continue
        _, st, geom, dj, bid, la, lo = data[k][f]
        if st not in ("dipindah", "dipindah_cek"): st = "belum_cocok"
        cf.execute(f'update "{T}" set geom=?, status_pindah=?, jarak_pindah_m=?, blob_id=?, lat_asli=?, lon_asli=? where fid=?',
                   (geom, st, dj, (k * 10000 + bid) if bid is not None else None, la, lo, f))
for nb, fl in groups.items():                       # satu nomor = satu status: kuning bila ada anggota yang perlu dicek
    sts = {r[0] for r in cf.execute(f'select status_pindah from "{T}" where no_bang=?', (nb,))}
    if "dipindah_cek" in sts and "dipindah" in sts:
        cf.execute(f'update "{T}" set status_pindah=? where no_bang=? and status_pindah=?', ("dipindah_cek", nb, "dipindah"))
cf.commit(); cf.close()
for c in conns: c.close()
cnt = collections.Counter(r[0] for r in sqlite3.connect(final).execute(f'select status_pindah from "{T}"'))
print("gabungan:", dict(cnt), "| peta penemu per kelompok:", dict(collections.Counter(maps[k] for k in chosen.values())))

# parkir
mainpng = os.path.join(ROOT, "geo", desa, maps[-1] + "_WSS.png"); mainpgw = mainpng[:-4] + ".pgw"
W, H = Image.open(mainpng).size
import numpy as np
inside = np.load(os.path.join(SCR, tags[-1] + "_inside.npy"))
ys_, xs_ = np.nonzero(inside); step = max(14, W // 120)
need = sum(1 for r in sqlite3.connect(final).execute(f'select status_pindah from "{T}"') if r[0] == "belum_cocok")
need = max(need, 1)
def plan():
    cols = max(1, (W - 80) // step // 3)
    rows_ = -(-need // cols)
    if ys_.max() + 60 + rows_ * step < H - 20:                       # bawah kotak titik
        return (80, ys_.max() + 60, step, step, cols)
    left = xs_.min() - 60
    if left > 80 + step * 4:                                          # kiri kotak titik
        c = max(1, (left - 40) // step); return (40, 60, step, step, c)
    right = W - (xs_.max() + 60)
    if right > step * 4:                                              # kanan kotak titik
        c = max(1, (right - 30) // step); return (xs_.max() + 60, 60, step, step, c)
    return (80, H - 70, step, step, 60)
px_, py_, dx_, dy_, pr_ = plan()
envp = dict(envb, PARK=f"{int(px_)},{int(py_)},{dx_},{dy_},{pr_}")
out_tmp = os.path.join(SCR, tags[-1] + "_final.gpkg")
r = subprocess.run([sys.executable, os.path.join(SCR, "park.py"), mainpgw, tags[-1], final, out_tmp], env=envp, capture_output=True, text=True)
print(r.stdout); print(r.stderr[-500:] if r.returncode else "")
out = os.path.join(ROOT, desa, kode + "_rapi_parkir.gpkg"); shutil.copyfile(out_tmp, out); print("disimpan:", out)
subprocess.run([sys.executable, os.path.join(SCR, "rekap.py"), ROOT], env=envb)
