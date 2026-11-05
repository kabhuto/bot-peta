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
                        "parkir": "Tidak jelas / tidak ditemukan, diparkir di luar batas SLS"}.get(r[1], "")
                detail.append([desa, sls, kode, r[0], r[1], st, ketr, r[2], float(r[3]) if r[3] else None, r[4], r[5], r[6], r[7]])
            c.close()
        else:
            c, t = feature_table(f)
            n = c.execute(f'select count(*) from "{t}"').fetchone()[0]; c.close()
            rekap.append([desa, sls, kode, n, None, None, None, None, "ABU", "Belum diproses", "Belum diproses"])

wb = Workbook()
HDR_SLS = ["Desa", "SLS", "Kode gpkg", "Jumlah titik", "Hijau (ditemukan)", "Kuning (cek manual)", "Merah (tidak jelas)", "% ditemukan", "Warna", "Keterangan", "Status proses"]
HDR_DET = ["Desa", "SLS", "Kode gpkg", "No bangunan", "Status", "Warna", "Keterangan", "Jarak pindah (m)", "Akurasi GPS (m)",
           "Lat asli", "Lon asli", "Lat baru/posisi sekarang", "Lon baru/posisi sekarang"]


def style_header(ws, row):
    for c in ws[row]:
        if c.value is not None:
            c.fill = head_fill; c.font = head_font; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def warna_desa(rs):
    proc_ = [r for r in rs if r[10] == "Sudah diproses"]
    if not proc_:
        return "ABU"
    if len(proc_) < len(rs):
        return "ABU"
    if all(r[8] == "HIJAU" for r in proc_):
        return "HIJAU"
    if sum(1 for r in proc_ if r[8] == "MERAH") * 2 > len(proc_):
        return "MERAH"
    return "KUNING"


desas = sorted({r[0] for r in rekap})

# --- lembar ringkasan per desa
wr = wb.active; wr.title = "Ringkasan"
wr.append(["Desa (folder)", "Jumlah SLS", "Sudah diproses", "Belum diproses", "SLS hijau", "SLS kuning", "SLS merah", "Total titik", "Titik hijau", "Titik kuning", "Titik merah", "Status desa"])
for d in desas:
    rs = [r for r in rekap if r[0] == d]; pr = [r for r in rs if r[10] == "Sudah diproses"]
    wr.append([d, len(rs), len(pr), len(rs) - len(pr),
               sum(1 for r in pr if r[8] == "HIJAU"), sum(1 for r in pr if r[8] == "KUNING"), sum(1 for r in pr if r[8] == "MERAH"),
               sum(r[3] for r in rs), sum(r[4] or 0 for r in pr), sum(r[5] or 0 for r in pr), sum(r[6] or 0 for r in pr),
               "Selesai" if len(pr) == len(rs) else ("Sebagian" if pr else "Belum diproses")])
    k = warna_desa(rs)
    for col in (1, 12):
        wr.cell(wr.max_row, col).fill = fills[k]
    for cell in wr[wr.max_row]:
        cell.border = border
wr.append(["TOTAL"] + [sum(wr.cell(r, c).value for r in range(2, wr.max_row + 1)) for c in range(2, 12)])
for cell in wr[wr.max_row]:
    cell.font = Font(bold=True); cell.border = border
style_header(wr, 1)
for i, w in enumerate([14, 11, 14, 14, 10, 11, 10, 12, 11, 12, 11, 16], 1):
    wr.column_dimensions[get_column_letter(i)].width = w
wr.freeze_panes = "A2"

# --- satu lembar per desa: tabel SLS di atas, detail titik di bawahnya
for d in desas:
    ws = wb.create_sheet(d)
    ws.append(["Desa " + d + " - rekap per SLS"]); ws.cell(1, 1).font = Font(bold=True, size=13)
    ws.append(HDR_SLS); style_header(ws, 2)
    for r in [r for r in rekap if r[0] == d]:
        ws.append(r)
        for cell in ws[ws.max_row]:
            cell.border = border
        for col in (1, 2, 3, 4, 9, 10, 11):
            ws.cell(ws.max_row, col).fill = fills[r[8]]
    dets = [x for x in detail if x[0] == d]
    ws.append([])
    ws.append(["Desa " + d + " - detail titik (SLS yang sudah diproses)"]); ws.cell(ws.max_row, 1).font = Font(bold=True, size=13)
    if dets:
        ws.append(HDR_DET); style_header(ws, ws.max_row)
        for r in dets:
            ws.append(r)
            for cell in ws[ws.max_row]:
                cell.border = border
            for col in range(1, 8):
                ws.cell(ws.max_row, col).fill = fills[r[5]]
    else:
        ws.append(["Belum ada SLS yang diproses di desa ini."])
    for i, w in enumerate([8, 11, 20, 13, 17, 14, 58, 14, 14, 13, 13, 18, 18], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A3"

proc = [r for r in rekap if r[10] == "Sudah diproses"]

wl = wb.create_sheet("Keterangan")
for line in [
    ["Warna", "Arti"],
    ["HIJAU", "Titik ditemukan dan sudah dipindah, tanpa perlu perbaikan atau cek manual."],
    ["KUNING", "Perlu cek manual: titik sudah dipindah tapi jaraknya jauh dibanding akurasi GPS, atau sebagian titik di SLS diparkir."],
    ["MERAH", "Tidak jelas: titik tidak ditemukan (diparkir di luar batas SLS). Untuk SLS: kurang dari separuh titik ditemukan."],
    ["ABU", "Belum diproses."],
    [],
    ["Catatan", "Pembacaan angka tulisan tangan dilakukan dari potongan gambar dan belum diukur akurasinya secara statistik. Periksa sampel hasil di QGIS."],
]:
    wl.append(line)
for c in wl[1]:
    c.fill = head_fill; c.font = head_font
for i, k in enumerate(["HIJAU", "KUNING", "MERAH", "ABU"], 2):
    wl.cell(i, 1).fill = fills[k]
wl.column_dimensions["A"].width = 12; wl.column_dimensions["B"].width = 120

out = os.path.join(root, "Rekap_bot_peta.xlsx")
wb.save(out)
print("tersimpan:", out)
print("SLS:", len(rekap), "| diproses:", len(proc), "| titik detail:", len(detail))
for r in proc:
    print(r[:10])
