import sys, os, json, math, sqlite3
import numpy as np
SCR = os.path.dirname(os.path.abspath(__file__))
pgw, tag = sys.argv[1:3]
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
PS = math.hypot(A, D) * math.cos(math.radians(7.15))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
c = sqlite3.connect(os.path.join(SCR, tag + ".gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
rows = c.execute(f'select no_bang,geotag_latitude,geotag_longitude,geotag_accuracy from "{t}"').fetchall()
gp = np.array([to_px(r[1], r[2]) for r in rows]); nb = [int(r[0]) if r[0] and r[0].isdigit() else None for r in rows]
acc = [float(r[3]) if r[3] else None for r in rows]
print("akurasi GPS di gpkg (m): median %.1f, p90 %.1f, maks %.1f" % (np.median([a for a in acc if a]), np.percentile([a for a in acc if a], 90), max(a for a in acc if a)))
reads = json.load(open(os.path.join(SCR, tag + "_reads.json")))
cand = {o["id"]: o for o in json.load(open(os.path.join(SCR, tag + "_cand.json")))}
same = 0; dists = []; samedist = []
for sid, num in reads.items():
    o = cand[int(sid)]
    d = np.hypot(gp[:, 0] - o["cx"], gp[:, 1] - o["cy"]); i = int(d.argmin())
    dists.append(d[i] * PS)
    if nb[i] == num:
        same += 1; samedist.append(d[i] * PS)
print("titik tangan -> titik gpkg TERDEKAT: median %.1f m; nomor sama pada %d dari %d" % (np.median(dists), same, len(reads)))
print("jarak ke titik gpkg terdekat (m): p25 %.1f, p75 %.1f, p90 %.1f" % tuple(np.percentile(dists, [25, 75, 90])))
