"""Pantau progres: python pantau.py [desa] [detik]  -- tampilan ulang tiap N detik (Ctrl+C untuk berhenti)

Hanya membaca <akar>\\<desa>\\*_rapi_parkir.gpkg; tidak mengubah apa pun.
Hijau = dipindah, Kuning = dipindah_cek, Merah = parkir/belum_cocok, Abu = belum ada hasil.
"""
import os, sys, glob, time, sqlite3
ROOT = r"D:\bot peta"
desa = sys.argv[1] if len(sys.argv) > 1 else "004"; jeda = int(sys.argv[2]) if len(sys.argv) > 2 else 30
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
