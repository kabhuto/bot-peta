"""Rekap hasil bot-peta ke Excel.

Membaca semua gpkg di <akar>\\<desa>\\*.gpkg. SLS yang sudah diproses punya berkas
<kode>_rapi_parkir.gpkg (kolom status_pindah). Hasil: <akar>\\Rekap_bot_peta.xlsx

Aturan warna per SLS (kolom % ditemukan = dipindah + dipindah_cek dibanding semua titik):
  HIJAU  : semua titik ditemukan tanpa perlu dicek (semua status 'dipindah')
  KUNING : ada titik yang perlu dicek manual ('dipindah_cek') atau sebagian diparkir,
           tapi minimal separuh titik ditemukan
  MERAH  : kurang dari separuh titik ditemukan / tidak jelas sama sekali
  ABU    : belum diproses
"""
import os, sys, sqlite3, glob
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

root = sys.argv[1] if len(sys.argv) > 1 else r"D:\bot peta"
FILL = {"HIJAU": "C6EFCE", "KUNING": "FFEB9C", "MERAH": "FFC7CE", "ABU": "D9D9D9"}
fills = {k: PatternFill("solid", fgColor=v) for k, v in FILL.items()}
thin = Side(style="thin", color="BBBBBB"); border = Border(left=thin, right=thin, top=thin, bottom=thin)
head_fill = PatternFill("solid", fgColor="1F4E78"); head_font = Font(bold=True, color="FFFFFF")


def feature_table(db):
    c = sqlite3.connect(db)
    return c, c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]


rekap, detail = [], []
for desa in sorted(d for d in os.listdir(root) if d.isdigit() and os.path.isdir(os.path.join(root, d))):
    folder = os.path.join(root, desa)
    asli = sorted(f for f in glob.glob(os.path.join(folder, "*.gpkg")) if not f.endswith("_rapi_parkir.gpkg"))
    for f in asli:
        kode = os.path.splitext(os.path.basename(f))[0]
        sls = kode[-6:]
        hasil = os.path.join(folder, kode + "_rapi_parkir.gpkg")
        if os.path.exists(hasil):
            c, t = feature_table(hasil)
            rows = c.execute(f'select no_bang,status_pindah,jarak_pindah_m,geotag_accuracy,lat_asli,lon_asli,geotag_latitude,geotag_longitude from "{t}" order by cast(no_bang as integer)').fetchall()
            n = len(rows)
            hij = sum(1 for r in rows if r[1] == "dipindah")
            kun = sum(1 for r in rows if r[1] == "dipindah_cek")
            mer = sum(1 for r in rows if r[1] == "parkir")
            ditemu = hij + kun
            if hij == n:
                warna, ket = "HIJAU", "Semua titik ditemukan tanpa perlu dicek"
            elif ditemu * 2 >= n:
                warna = "KUNING"
                ket = f"{kun} titik perlu cek manual, {mer} titik diparkir"
            else:
                warna, ket = "MERAH", f"Hanya {ditemu} dari {n} titik ditemukan"
            rekap.append([desa, sls, kode, n, hij, kun, mer, round(100 * ditemu / n, 1) if n else 0, warna, ket, "Sudah diproses"])
            for r in rows:
                st = {"dipindah": "HIJAU", "dipindah_cek": "KUNING", "parkir": "MERAH"}.get(r[1], "ABU")
                ketr = {"dipindah": "Ditemukan", "dipindah_cek": "Perlu cek manual (jarak pindah jauh dibanding akurasi GPS)",
                        "parkir": "KERJAKAN MANUAL: tulisan tangan tidak terlihat/tidak terbaca, titik diparkir di luar batas SLS"}.get(r[1], "")
                detail.append([desa, sls, kode, r[0], r[1], st, ketr, r[2], float(r[3]) if r[3] else None, r[4], r[5], r[6], r[7], None, None])
            c.close()
        else:
            c, t = feature_table(f)
            n = c.execute(f'select count(*) from "{t}"').fetchone()[0]; c.close()
            rekap.append([desa, sls, kode, n, None, None, None, None, "ABU", "Belum diproses", "Belum diproses"])

HDR_SLS = ["Desa", "SLS", "Kode gpkg", "Jumlah titik", "Hijau (ditemukan)", "Kuning (cek manual)", "Merah (tidak jelas)", "% ditemukan", "Warna", "Keterangan", "Status proses"]
HDR_DET = ["Desa", "SLS", "Kode gpkg", "No bangunan", "Status", "Warna", "Keterangan", "Jarak pindah (m)", "Akurasi GPS (m)",
           "Lat asli", "Lon asli", "Lat baru/posisi sekarang", "Lon baru/posisi sekarang", "Dikerjakan manual? (isi Ya)", "Catatan manual"]


def style_header(ws, row):
    for c in ws[row]:
        if c.value is not None:
            c.fill = head_fill; c.font = head_font; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


desas = sorted({r[0] for r in rekap})
for d in desas:
    rs = [r for r in rekap if r[0] == d]; pr = [r for r in rs if r[10] == "Sudah diproses"]
    wb = Workbook()
    ws = wb.active; ws.title = "Rekap SLS"
    ws.append(HDR_SLS); style_header(ws, 1)
    for r in rs:
        ws.append(r)
        for cell in ws[ws.max_row]:
            cell.border = border
        for col in (1, 2, 3, 4, 9, 10, 11):
            ws.cell(ws.max_row, col).fill = fills[r[8]]
    ws.append([])
    ws.append(["Ringkasan desa " + d]); ws.cell(ws.max_row, 1).font = Font(bold=True)
    for label, val in [("Jumlah SLS", len(rs)), ("Sudah diproses", len(pr)), ("Belum diproses", len(rs) - len(pr)),
                       ("SLS hijau", sum(1 for r in pr if r[8] == "HIJAU")), ("SLS kuning", sum(1 for r in pr if r[8] == "KUNING")),
                       ("SLS merah", sum(1 for r in pr if r[8] == "MERAH")), ("Total titik", sum(r[3] for r in rs)),
                       ("Titik hijau", sum(r[4] or 0 for r in pr)), ("Titik kuning", sum(r[5] or 0 for r in pr)), ("Titik merah", sum(r[6] or 0 for r in pr))]:
        ws.append([label, val])
    for i_, w in enumerate([8, 11, 20, 13, 17, 14, 14, 12, 10, 52, 16], 1):
        ws.column_dimensions[get_column_letter(i_)].width = w
    ws.freeze_panes = "A2"

    wd = wb.create_sheet("Detail titik")
    wd.append(HDR_DET); style_header(wd, 1)
    for r in [x for x in detail if x[0] == d]:
        wd.append(r)
        for cell in wd[wd.max_row]:
            cell.border = border
        for col in range(1, 8):
            wd.cell(wd.max_row, col).fill = fills[r[5]]
    for i_, w in enumerate([8, 11, 20, 13, 17, 14, 70, 14, 14, 13, 13, 18, 18, 18, 30], 1):
        wd.column_dimensions[get_column_letter(i_)].width = w
    wd.freeze_panes = "A2"; wd.auto_filter.ref = wd.dimensions

    wl = wb.create_sheet("Keterangan")
    for line in [["Warna", "Arti"],
                 ["HIJAU", "Titik ditemukan dan sudah dipindah, tanpa perlu perbaikan atau cek manual."],
                 ["KUNING", "Perlu cek manual: titik sudah dipindah tapi jaraknya jauh dibanding akurasi GPS, atau sebagian titik di SLS diparkir."],
                 ["MERAH", "Tidak jelas / tidak ditemukan: titik diparkir di luar batas SLS, KERJAKAN MANUAL."],
                 ["ABU", "Belum diproses (atau peta tidak tersedia)."]]:
        wl.append(line)
    style_header(wl, 1)
    for i_, k in enumerate(["HIJAU", "KUNING", "MERAH", "ABU"], 2):
        wl.cell(i_, 1).fill = fills[k]
    wl.column_dimensions["A"].width = 12; wl.column_dimensions["B"].width = 120
    out = os.path.join(root, "Rekap_" + d + ".xlsx")
    wb.save(out); print("tersimpan:", out, "| SLS:", len(rs), "diproses:", len(pr))
