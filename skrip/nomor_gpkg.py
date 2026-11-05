"""Daftar nomor unik (angka) di gpkg asli satu SLS: python nomor_gpkg.py <desa> <sls>"""
import sqlite3, sys
desa, sls = sys.argv[1:3]
c = sqlite3.connect(rf"D:\bot peta\{desa}\3526020{desa}{sls}.gpkg")
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
print(sorted({int(r[0]) for r in c.execute(f'select no_bang from "{t}"') if r[0] and str(r[0]).isdigit()}))
