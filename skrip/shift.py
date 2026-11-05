import sys, os, json, math, sqlite3
import numpy as np
SCR = os.path.dirname(os.path.abspath(__file__))
pgw, tag = sys.argv[1:3]
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
Minv = np.linalg.inv(np.array([[A, B], [D, E]]))
def to_px(lat, lon):
    x = lon * 6378137.0 * math.pi / 180.0
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return Minv @ np.array([x - C, y - F])
c = sqlite3.connect(os.path.join(SCR, tag + ".gpkg"))
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
pts = [(nb, to_px(la, lo)) for nb, la, lo in c.execute(f'select no_bang,geotag_latitude,geotag_longitude from "{t}"')]
reads = json.load(open(os.path.join(SCR, tag + "_reads.json")))
cand = {o["id"]: o for o in json.load(open(os.path.join(SCR, tag + "_cand.json")))}
# untuk tiap bacaan yang yakin (angka 1-digit/2-digit jelas), cari titik gpkg bernomor sama PALING dekat, tanpa batas radius
vec = []
for sid, num in reads.items():
    o = cand[int(sid)]
    same = [p for nb, p in pts if nb and nb.isdigit() and int(nb) == num]
    if not same: continue
    p = min(same, key=lambda p: np.hypot(p[0] - o["cx"], p[1] - o["cy"]))
    vec.append((int(sid), num, o["cx"] - p[0], o["cy"] - p[1], float(np.hypot(p[0] - o["cx"], p[1] - o["cy"]))))
v = np.array([[a[2], a[3]] for a in vec]); dd = np.array([a[4] for a in vec])
print("bacaan yang nomornya ada di gpkg:", len(vec), "dari", len(reads))
print("jarak ke titik bernomor sama (px): median %.0f, p25 %.0f, p75 %.0f" % (np.median(dd), np.percentile(dd, 25), np.percentile(dd, 75)))
near = dd < 150
print("yang <150px:", near.sum(), "vektor rata2 (px):", v[near].mean(axis=0), "sebaran:", v[near].std(axis=0))
for a in sorted(vec, key=lambda a: a[4])[:15]:
    print(a)
