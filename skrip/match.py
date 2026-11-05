import sys, os, json, math, sqlite3, shutil, struct, collections
import numpy as np

SCR = os.path.dirname(os.path.abspath(__file__))
pgw, tag, outp = sys.argv[1:4]

A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
M = np.array([[A, B], [D, E]]); Minv = np.linalg.inv(M)
PS = math.hypot(A, D) * math.cos(math.radians(7.15))  # meter per piksel
R = float(os.environ.get('RM', 12)) / PS
print('meter/piksel: %.4f; radius pencocokan: %.0f px' % (PS, R))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
def to_ll(col, row):
    x, y = M @ np.array([col, row]) + np.array([C, F])
    lon = x / 6378137.0 * 180.0 / math.pi
    lat = math.degrees(2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2)
    return lat, lon

reads = json.load(open(os.path.join(SCR, tag + "_reads.json")))  # {"id": nomor}
cand = {o["id"]: o for o in json.load(open(os.path.join(SCR, tag + "_cand.json")))}

shutil.copyfile(os.path.join(SCR, tag + ".gpkg"), outp)
c = sqlite3.connect(outp)
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
# buang indeks rtree (butuh fungsi ST_*), QGIS tetap bisa membuka tanpanya
for (n,) in c.execute("select name from sqlite_master where type='trigger' and name like 'rtree_%'").fetchall():
    c.execute(f'drop trigger "{n}"')
for (n,) in c.execute("select name from sqlite_master where type='table' and name like 'rtree_%'").fetchall():
    try:
        c.execute(f'drop table if exists "{n}"')
    except sqlite3.OperationalError:
        pass
c.execute("delete from gpkg_extensions where extension_name='gpkg_rtree_index'")
for col, typ in (("lat_asli", "REAL"), ("lon_asli", "REAL"), ("status_pindah", "TEXT"), ("jarak_pindah_m", "REAL"), ("blob_id", "INTEGER")):
    c.execute(f'alter table "{t}" add column {col} {typ}')

pts = []
for fid, nb, lat, lon, blob, acc in c.execute(f'select fid,no_bang,geotag_latitude,geotag_longitude,geom,geotag_accuracy from "{t}"'):
    px = to_px(lat, lon)
    pts.append(dict(acc=float(acc) if acc else 0.0, fid=fid, nb=nb, num=int(nb) if nb and nb.isdigit() else None, lat=lat, lon=lon, px=px, blob=blob))

moved = {}; log_mismatch = []
for sid, num in sorted(reads.items(), key=lambda kv: int(kv[0])):
    o = cand[int(sid)]
    near = [p for p in pts if p["num"] == num and np.hypot(p["px"][0] - o["cx"], p["px"][1] - o["cy"]) <= R]
    if not near:
        around = sorted({p["num"] for p in pts if np.hypot(p["px"][0] - o["cx"], p["px"][1] - o["cy"]) <= R and p["num"] is not None})
        log_mismatch.append((int(sid), num, around))
        continue
    for p in near:
        if p["fid"] in moved and moved[p["fid"]][2] < np.hypot(p["px"][0] - o["cx"], p["px"][1] - o["cy"]):
            continue
        moved[p["fid"]] = (o["cx"], o["cy"], float(np.hypot(p["px"][0] - o["cx"], p["px"][1] - o["cy"])), int(sid))

for p in pts:
    if p["fid"] in moved:
        cx, cy, dpx, sid = moved[p["fid"]]
        lat, lon = to_ll(cx, cy)
        hdr = p["blob"][:8]
        newblob = hdr + struct.pack("<BIdd", 1, 1, lon, lat)
        c.execute(f'update "{t}" set geom=?, lat_asli=?, lon_asli=?, status_pindah=?, jarak_pindah_m=?, blob_id=? where fid=?',
                  (newblob, p["lat"], p["lon"], "dipindah" if dpx * PS <= max(float(os.environ.get("CEKM", 20)), 1.5 * p["acc"]) else "dipindah_cek", round(dpx * PS, 1), sid, p["fid"]))
    else:
        c.execute(f'update "{t}" set lat_asli=?, lon_asli=?, status_pindah=? where fid=?', (p["lat"], p["lon"], "belum_cocok", p["fid"]))
c.commit()

n = len(pts); m = len(moved)
print(f"titik gpkg: {n}; dipindah: {m}; belum cocok: {n - m}")
print("bacaan tidak cocok dengan nomor terdekat:", len(log_mismatch))
for sid, num, around in log_mismatch:
    print(f"  #{sid} dibaca {num}; nomor gpkg terdekat: {around}")
dist = [v[2] * PS for v in moved.values()]
print("jarak pindah (m): median %.1f, maks %.1f" % (np.median(dist), max(dist)))
# cek titik ganda yang sudah menumpuk
grp = collections.defaultdict(set)
for fid, (cx, cy, d_, sid) in moved.items():
    grp[[p for p in pts if p["fid"] == fid][0]["nb"]].add(sid)
print("nomor ganda yang titiknya terbagi ke >1 coretan:", {k: sorted(v) for k, v in grp.items() if len(v) > 1})
