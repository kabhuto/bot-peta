"""Selesaikan satu SLS: python finish.py <desa> <sls> [RM_meter]
Membutuhkan s<sls>_cand.json dan s<sls>_reads.json di folder skrip (hasil prep.py + pembacaan manual).
Langkah: cocokkan nomor (nomor gpkg yang sama ditumpuk di satu tulisan), parkir yang tidak ketemu di luar batas SLS,
simpan ke <akar>\<desa>\<kode>_rapi_parkir.gpkg, lalu perbarui rekap Excel."""
import os, sys, subprocess
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
desa, sls = sys.argv[1:3]; RM = sys.argv[3] if len(sys.argv) > 3 else "400"
tag = "s" + sls; kode = "3526020" + desa + sls
png = os.path.join(ROOT, "geo", desa, sls + "_WSS.png"); pgw = png[:-4] + ".pgw"
W, H = Image.open(png).size
draft = os.path.join(SCR, tag + "_draft.gpkg"); final = os.path.join(SCR, tag + "_final.gpkg")
env = dict(os.environ, RM=RM, PARK=f"200,{H-70},{max(14, W//120)},{max(14, W//120)},60", PYTHONIOENCODING="utf-8")
r = subprocess.run([sys.executable, os.path.join(SCR, "match.py"), pgw, tag, draft], env=env, capture_output=True, text=True)
print("\n".join(l for l in r.stdout.splitlines() if "nomor gpkg terdekat" not in l)); print(r.stderr[-400:] if r.returncode else "")
r = subprocess.run([sys.executable, os.path.join(SCR, "park.py"), pgw, tag, draft, final], env=env, capture_output=True, text=True)
print(r.stdout); print(r.stderr[-400:] if r.returncode else "")
out = os.path.join(ROOT, desa, kode + "_rapi_parkir.gpkg")
import shutil; shutil.copyfile(final, out); print("disimpan:", out)
subprocess.run([sys.executable, os.path.join(SCR, "rekap.py"), ROOT], env=env)
