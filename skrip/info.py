"""Info tiap SLS dalam satu folder desa: ukuran piksel georeferensi (m/px), jumlah titik, akurasi GPS, lokasi berkas."""
import os, sys, math, glob, sqlite3
root = r"D:\bot peta"
desa = sys.argv[1]
geo = os.path.join(root, "geo", desa)
for f in sorted(glob.glob(os.path.join(root, desa, "*.gpkg"))):
    kode = os.path.basename(f)[:-5]
    if kode.endswith("_rapi_parkir"):
        continue
    sls = kode[-6:]
    c = sqlite3.connect(f)
    t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
    n, lat = c.execute(f'select count(*),avg(geotag_latitude) from "{t}"').fetchone()
    acc = [float(r[0]) for r in c.execute(f'select geotag_accuracy from "{t}"') if r[0]]
    uniq = c.execute(f'select count(distinct no_bang) from "{t}"').fetchone()[0]
    maxn = c.execute(f'select max(cast(no_bang as integer)) from "{t}"').fetchone()[0]
    pgw = os.path.join(geo, sls + "_WSS.pgw")
    ps = None
    if os.path.exists(pgw):
        A, D = [float(x) for x in open(pgw).read().split()[:2]]
        ps = math.hypot(A, D) * math.cos(math.radians(-lat))
    ada = os.path.exists(os.path.join(geo, sls + "_WSS.png"))
    print(f"{sls}: titik={n} unik={uniq} maks={maxn} akurasi_median={sorted(acc)[len(acc)//2] if acc else None} m/px={ps and round(ps,4)} png={ada}")
