"""Laporan penyebab SLS belum/kurang terbaca: python diagnosa.py  -> D:\\bot peta\\Laporan_masalah_SLS.xlsx

Per SLS: titik, status hasil (hijau/kuning/merah), skala peta (m/px), titik hitam terdeteksi vs titik gpkg,
akurasi GPS, ada tidaknya peta, dan penyebab utama yang disimpulkan dari angka-angka itu.
"""
import os, re, glob, math, sqlite3
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
kand = {}
for l in open(os.path.join(SCR, "semua_log.txt"), encoding="utf-8"):
    m = re.match(r"\[\d\d:\d\d:\d\d\] (\d+)/(\d+): prep", l)
    if m: cur = (m.group(1), m.group(2))
    m = re.search(r"titik hitam kandidat: (\d+)", l)
    if m: kand[cur] = int(m.group(1))
rows = []
for dd in sorted(d for d in os.listdir(ROOT) if re.fullmatch(r"\d{3}", d)):
    for f in sorted(glob.glob(os.path.join(ROOT, dd, "*.gpkg"))):
        k = os.path.basename(f)[:-5]
        if k.endswith("_rapi_parkir"): continue
        sls = k[-6:]
        c = sqlite3.connect(f); T = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
        n, lat = c.execute(f'select count(*),avg(geotag_latitude) from "{T}"').fetchone()
        acc = sorted(float(r[0]) for r in c.execute(f'select geotag_accuracy from "{T}"') if r[0])
        med = acc[len(acc) // 2] if acc else None
        pgw = os.path.join(ROOT, "geo", dd, sls + "_WSS.pgw"); ada = os.path.exists(pgw) and os.path.exists(pgw[:-4] + ".png")
        ps = None
        if ada:
            A, D = [float(x) for x in open(pgw).read().split()[:2]]; ps = math.hypot(A, D) * math.cos(math.radians(-lat))
        g = y = m = None
        o = os.path.join(ROOT, dd, k + "_rapi_parkir.gpkg")
        if os.path.exists(o):
            c2 = sqlite3.connect(o); d = dict(c2.execute(f'select status_pindah,count(*) from "{T}" group by 1').fetchall())
            g = d.get("dipindah", 0); y = d.get("dipindah_cek", 0); m = n - g - y
        kd = kand.get((dd, sls)); sebab = []
        if not ada: sebab.append("TIDAK ADA peta/georeferensi untuk SLS ini (hanya gpkg)")
        else:
            if ps and ps > 0.6: sebab.append(f"skala peta kecil ({ps:.2f} m/px): tulisan tangan terlalu kecil untuk dibaca")
            if kd is not None and kd < 0.5 * n: sebab.append(f"titik hitam hanya terdeteksi {kd} dari {n} titik gpkg: gaya peta/kontras berbeda dari 004 (citra gelap, titik tertimpa tulisan)")
            if med and med > 8: sebab.append(f"akurasi GPS rendah (median {med:.0f} m): titik gpkg jauh dari bangunan")
            if g is not None and g + y == 0 and not sebab: sebab.append("belum dibaca (tulisan tangan belum dikerjakan)")
            elif g is not None and g + y == 0: sebab.append("belum dibaca (tulisan tangan belum dikerjakan)")
        rows.append((dd, sls, n, g, y, m, ps, kd, med, "; ".join(sebab) or "ok"))
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Penyebab per SLS"
head = ["Desa", "SLS", "Titik gpkg", "Hijau", "Kuning", "Merah", "Skala (m/px)", "Titik hitam terdeteksi", "Akurasi GPS median (m)", "Penyebab / catatan"]
ws.append(head)
for c in ws[1]: c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="D9E1F2")
fill = {"merah": "FFC7CE", "kuning": "FFEB9C", "hijau": "C6EFCE", "abu": "D9D9D9"}
for r in rows:
    ws.append([r[0], r[1], r[2], r[3], r[4], r[5], round(r[6], 2) if r[6] else None, r[7], round(r[8], 1) if r[8] else None, r[9]])
    row = ws[ws.max_row]
    if r[3] is None: col = "abu"
    elif r[2] and r[3] / r[2] >= 0.9: col = "hijau"
    elif r[2] and (r[3] + r[4]) / r[2] >= 0.5: col = "kuning"
    else: col = "merah"
    for c in row: c.fill = PatternFill("solid", fgColor=fill[col])
for i, w in enumerate([7, 9, 11, 8, 8, 8, 12, 20, 20, 110], 1): ws.column_dimensions[chr(64 + i)].width = w
out = os.path.join(ROOT, "Laporan_masalah_SLS.xlsx"); wb.save(out)
sebab_hit = {}
for r in rows:
    for s in r[9].split("; "): sebab_hit[re.sub(r"[\d.,]+", "#", s)[:60]] = sebab_hit.get(re.sub(r"[\d.,]+", "#", s)[:60], 0) + 1
print("tersimpan:", out, "| SLS:", len(rows))
for s, n in sorted(sebab_hit.items(), key=lambda kv: -kv[1]): print(f"  {n:3} SLS  {s}")
