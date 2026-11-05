"""Proses otomatis semua SLS yang belum punya hasil: python semua.py [desa1,desa2,...]

Untuk tiap SLS yang punya peta (png+pgw): prep.py -> s<sls>_reads.json kosong (bila belum ada) -> finish.py.
Tanpa bacaan tulisan semuanya diparkir (merah); pembacaan menyusul dan finish.py dijalankan ulang.
SLS tanpa peta dilewati dan dicatat. Log: semua_log.txt di folder skrip.
"""
import os, sys, glob, json, subprocess, time
SCR = os.path.dirname(os.path.abspath(__file__)); ROOT = r"D:\bot peta"
sys.path.insert(0, SCR)
from tagutil import tag_for
desas = sys.argv[1].split(",") if len(sys.argv) > 1 else [os.path.basename(d) for d in sorted(glob.glob(os.path.join(ROOT, "0*"))) if os.path.basename(d) != "geo"]
env = dict(os.environ, AROUND="60", MAXV="80", ERO="1", PYTHONIOENCODING="utf-8", AMBPX="15")
for k in ("SISA", "INK", "MAP", "LINE", "NEWONLY"): env.pop(k, None)
log = open(os.path.join(SCR, "semua_log.txt"), "a", encoding="utf-8")
def tulis(s):
    print(s, flush=True); log.write(s + "\n"); log.flush()
for desa in desas:
    for f in sorted(glob.glob(os.path.join(ROOT, desa, "*.gpkg"))):
        kode = os.path.basename(f)[:-5]
        if kode.endswith("_rapi_parkir"): continue
        sls = kode[-6:]
        if os.path.exists(os.path.join(ROOT, desa, kode + "_rapi_parkir.gpkg")): continue
        png = os.path.join(ROOT, "geo", desa, sls + "_WSS.png")
        if not os.path.exists(png) or not os.path.exists(png[:-4] + ".pgw"):
            tulis(f"[{time.strftime('%H:%M:%S')}] {desa}/{sls}: TIDAK ADA PETA/GEOREF -> dilewati"); continue
        tulis(f"[{time.strftime('%H:%M:%S')}] {desa}/{sls}: prep ...")
        r = subprocess.run([sys.executable, os.path.join(SCR, "prep.py"), desa, sls, "120"], env=env, capture_output=True, text=True, cwd=SCR)
        if r.returncode: tulis(f"   prep GAGAL: {r.stderr[-300:]}"); continue
        tulis("   " + next((l for l in r.stdout.splitlines() if "kandidat" in l), ""))
        rp = os.path.join(SCR, f"{tag_for(desa, sls)}_reads.json")
        if not os.path.exists(rp): json.dump({}, open(rp, "w"))
        r = subprocess.run([sys.executable, os.path.join(SCR, "finish.py"), desa, sls, sls, "2000"], env=env, capture_output=True, text=True, cwd=SCR)
        ok = "disimpan" in r.stdout
        tulis("   " + (next((l for l in r.stdout.splitlines() if l.startswith("gabungan")), "") if ok else f"finish GAGAL: {(r.stdout + r.stderr)[-300:]}"))
tulis(f"[{time.strftime('%H:%M:%S')}] SELESAI")
