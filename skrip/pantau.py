"""Pantau progres: python pantau.py [desa] [detik]  -- tampilan ulang tiap N detik (Ctrl+C untuk berhenti)

Hanya membaca <akar>\\<desa>\\*_rapi_parkir.gpkg; tidak mengubah apa pun.
Hijau = dipindah, Kuning = dipindah_cek, Merah = parkir/belum_cocok, Abu = belum ada hasil.
"""
import os, sys, glob, time, sqlite3
ROOT = r"D:\bot peta"
desa = sys.argv[1] if len(sys.argv) > 1 else "004"; jeda = int(sys.argv[2]) if len(sys.argv) > 2 else 30
if desa == "semua":                                  # ringkasan satu baris per folder desa
    desas = [os.path.basename(d) for d in sorted(glob.glob(os.path.join(ROOT, "0*"))) if os.path.basename(d) != "geo"]
    while True:
        os.system("cls"); print(f"PROGRES SEMUA FOLDER   {time.strftime('%H:%M:%S')}  (tiap {jeda} dtk, Ctrl+C = berhenti)\n")
        print(f"{'Desa':6}{'SLS':>5}{'Diproses':>9}{'Titik':>8}{'Hijau':>7}{'Kuning':>8}{'Merah':>7}{'Belum':>7}")
        G = [0] * 6
        for dd in desas:
            ks = sorted({os.path.basename(f)[:-5].replace("_rapi_parkir", "") for f in glob.glob(os.path.join(ROOT, dd, "*.gpkg"))})
            sls = len(ks); proc = n = g = y = m = belum = 0
            for k in ks:
                f = os.path.join(ROOT, dd, k + "_rapi_parkir.gpkg"); src = os.path.join(ROOT, dd, k + ".gpkg")
                if os.path.exists(f):
                    c = sqlite3.connect(f); t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
                    d = dict(c.execute(f'select status_pindah,count(*) from "{t}" group by 1').fetchall()); tt = sum(d.values())
                    proc += 1; n += tt; g += d.get("dipindah", 0); y += d.get("dipindah_cek", 0); m += tt - d.get("dipindah", 0) - d.get("dipindah_cek", 0)
                else:
                    c = sqlite3.connect(src); t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
                    belum += c.execute(f'select count(*) from "{t}"').fetchone()[0]
            print(f"{dd:6}{sls:5}{proc:9}{n:8}{g:7}{y:8}{m:7}{belum:7}")
            for i, v in enumerate((sls, proc, n, g, y, m)): G[i] += v
        print(f"\n{'TOTAL':6}{G[0]:5}{G[1]:9}{G[2]:8}{G[3]:7}{G[4]:8}{G[5]:7}")
        time.sleep(jeda)
def kode_semua():
    out = set()
    for f in glob.glob(os.path.join(ROOT, desa, "*.gpkg")):
        b = os.path.basename(f)[:-5]; out.add(b[:-len("_rapi_parkir")] if b.endswith("_rapi_parkir") else b)
    return sorted(out)
while True:
    os.system("cls")
    print(f"PROGRES bot-peta folder {desa}   {time.strftime('%H:%M:%S')}   (diperbarui tiap {jeda} dtk, Ctrl+C = berhenti)\n")
    print(f"{'SLS':8}{'Titik':>7}{'Hijau':>7}{'Kuning':>8}{'Merah':>7}   {'% terpindah':>11}   Diubah")
    tot = [0, 0, 0, 0]
    for k in kode_semua():
        f = os.path.join(ROOT, desa, k + "_rapi_parkir.gpkg")
        if not os.path.exists(f):
            c = sqlite3.connect(os.path.join(ROOT, desa, k + ".gpkg")); t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
            n = c.execute(f'select count(*) from "{t}"').fetchone()[0]
            print(f"{k[-6:]:8}{n:7}{'-':>7}{'-':>8}{'-':>7}   {'(belum diproses)':>11}"); tot[0] += n; continue
        c = sqlite3.connect(f); t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
        d = dict(c.execute(f'select status_pindah,count(*) from "{t}" group by 1').fetchall())
        n = sum(d.values()); g = d.get("dipindah", 0); y = d.get("dipindah_cek", 0); m = n - g - y
        print(f"{k[-6:]:8}{n:7}{g:7}{y:8}{m:7}   {100*(g+y)/n:10.0f}%   {time.strftime('%H:%M', time.localtime(os.path.getmtime(f)))}")
        tot[0] += n; tot[1] += g; tot[2] += y; tot[3] += m
    print(f"\n{'TOTAL':8}{tot[0]:7}{tot[1]:7}{tot[2]:8}{tot[3]:7}   {100*(tot[1]+tot[2])/max(1,tot[0]):10.0f}%")
    time.sleep(jeda)
