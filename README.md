# bot-peta

Skrip bantu untuk memindahkan titik geotag (gpkg) ke posisi nomor tulisan tangan
pada peta WSS hasil scan yang sudah digeoreferensi. Dibuat dan diuji pada peta
bergaya "titik hitam + nomor di bawahnya" (contoh: SLS 3526020004000101).

**Status: prototipe.** Skrip masih berupa kumpulan langkah terpisah, bukan alat satu klik.
Jalur file masih diisi lewat argumen, dan pembacaan angka tulisan tangan dilakukan
manual dari lembar potongan gambar (bukan OCR otomatis).

## Kebutuhan
Python 3.10+ dengan `numpy`, `pillow`, `scipy`. Tanpa GDAL/OpenCV. Memakai `sqlite3` bawaan Python.

## Masukan
- `NNNNNN_WSS.png` + `.pgw`: peta scan georeferensi (EPSG:3857).
- `<kode>.gpkg`: layer titik dengan kolom `no_bang`, `geotag_latitude`, `geotag_longitude`, `geotag_accuracy`.

## Alur
1. `overlay.py`: menumpuk titik gpkg di atas peta untuk memeriksa georeferensi.
2. `boundary.py`: mengambil batas SLS dari garis merah di gambar (isi area tertutup), simpan `*_inside.npy`.
3. `dots.py` / `dots2.py`: mendeteksi titik hitam tulisan tangan dan membuat lembar potongan di bawah tiap titik. Titik pusat ditandai lingkaran merah.
4. Baca nomor tiap potongan, simpan sebagai `{id_titik: nomor}` di `<tag>_reads.json`, dan posisi titik di `<tag>_cand.json`.
5. `match.py`: mencocokkan nomor terbaca dengan `no_bang` di gpkg. Nomor ganda di gpkg ikut menumpuk ke satu koordinat. Status `dipindah`, `dipindah_cek` (jarak jauh dibanding akurasi GPS), atau `belum_cocok`. Koordinat lama disimpan di `lat_asli`/`lon_asli`.
6. `park.py`: memarkir titik `belum_cocok` di luar batas SLS (status `parkir`).
7. `rekap.py`: membuat `Rekap_bot_peta.xlsx` (lembar Ringkasan + satu lembar per folder desa, berwarna hijau/kuning/merah/abu).
8. `verify_sheets.py`, `nearest.py`, `shift.py`, `around.py`: alat pemeriksaan.

## Aturan
- Nomor tulisan tangan tanpa titik gpkg: dilewati.
- Titik gpkg tanpa tulisan: diparkir di luar batas SLS.
- File gpkg asli tidak pernah ditimpa. Hasil ditulis ke salinan.

## Batasan
- Belum mendukung gaya nomor yang dilingkari oval tangan.
- Pembacaan angka belum diukur akurasinya secara statistik. Periksa hasil di QGIS.

## Alur per SLS (versi terbaru)
```
set MAP=<nama peta, mis. "000102_Inset 1">   (opsional; bawaan = nomor SLS)
python skrip/prep.py <desa> <sls> 30            # batas SLS, deteksi titik hitam, lembar potongan + kandidat nomor gpkg
# baca lembar -> isi skrip/s<peta>_reads.json  ({"id potongan": nomor})
python skrip/finish.py <desa> <sls> "<inset1>,<inset2>,<peta utama>" 400
```
- `finish.py` mencocokkan, menumpuk titik gpkg bernomor sama di satu tulisan (inset lebih dulu, peta utama terakhir),
  memarkir yang tidak ditemukan di luar batas SLS, menyimpan `<kode>_rapi_parkir.gpkg`, dan memperbarui Excel.
- Variabel lingkungan: `MAXV`, `SAT`, `ERO` (deteksi tinta), `LINE=warm` (batas SLS oranye), `GAP`.
- Excel (`rekap.py`) punya kolom "Dikerjakan manual?" dan "Catatan manual" untuk titik parkir.
