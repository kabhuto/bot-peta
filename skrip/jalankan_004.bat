@echo off
chcp 65001 >nul
title bot-peta: hitung ulang semua SLS folder 004
cd /d D:\2026\bot-peta\skrip
set PYTHONIOENCODING=utf-8
set AMBPX=15
echo ===== 000101 =====
set AMBPX=45
python finish.py 004 000101 "000101" 2000 | findstr /C:"gabungan" /C:"nomor hasil" /C:"diparkir" /C:"Traceback"
set AMBPX=15
echo ===== 000102 (inset + utama) =====
python finish.py 004 000102 "000102_Inset 1,000102" 2000 | findstr /C:"gabungan" /C:"nomor hasil" /C:"diparkir" /C:"Traceback"
echo ===== 000103 (inset + utama) =====
set LINE=warm
python finish.py 004 000103 "000103_Inset 1,000103" 2000 | findstr /C:"gabungan" /C:"nomor hasil" /C:"diparkir" /C:"Traceback"
set LINE=
for %%S in (000200 000301 000302 000500 000600) do (
  echo ===== %%S =====
  python finish.py 004 %%S "%%S" 2000 | findstr /C:"gabungan" /C:"diparkir" /C:"Traceback"
)
echo ===== Excel =====
python rekap.py | findstr "004"
echo.
echo SELESAI. Hasil: D:\bot peta\004\  dan  D:\bot peta\Rekap_004.xlsx
pause
