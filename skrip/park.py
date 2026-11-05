import sys, os, math, sqlite3, shutil, struct
import numpy as np
SCR = os.path.dirname(os.path.abspath(__file__))
pgw, tag, src, outp = sys.argv[1:5]
A, D, B, E, C, F = [float(x) for x in open(pgw).read().split()]
M = np.array([[A, B], [D, E]])
def to_ll(col, row):
    x, y = M @ np.array([col, row]) + np.array([C, F])
    return math.degrees(2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2), x / 6378137.0 * 180.0 / math.pi
inside = np.load(os.path.join(SCR, tag + "_inside.npy"))
H, W = inside.shape

shutil.copyfile(src, outp)
c = sqlite3.connect(outp)
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
c.execute(f'alter table "{t}" add column urut_parkir INTEGER')
rows = c.execute(f'select fid,no_bang,geom from "{t}" where status_pindah=? order by no_bang, fid', ("belum_cocok",)).fetchall()
# baris parkir di bawah bingkai peta (area legenda), jarak 20 px (~5,7 m)
X0, Y0, DX, DY, PERROW = [int(v) for v in os.environ.get('PARK', '300,2590,20,24,70').split(',')]
ok = True
slot = {}                                   # satu nomor = satu posisi parkir (nomor ganda ditumpuk)
for k, (fid, nb, blob) in enumerate(rows):
    if nb not in slot:
        slot[nb] = len(slot)
    j = slot[nb]
    col = X0 + (j % PERROW) * DX
    row = Y0 + (j // PERROW) * DY
    if row < H and col < W and inside[int(row), int(col)]:
        ok = False
    lat, lon = to_ll(col, row)
    newblob = blob[:8] + struct.pack("<BIdd", 1, 1, lon, lat)
    c.execute(f'update "{t}" set geom=?, status_pindah=?, urut_parkir=? where fid=?', (newblob, "parkir", j + 1, fid))
c.commit()
print("titik diparkir:", len(rows), "| posisi parkir (nomor unik):", len(slot), "| semua di luar batas SLS:", ok)
print(c.execute(f'select status_pindah,count(*) from "{t}" group by 1').fetchall())
