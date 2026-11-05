"""Nama berkas kerja per (desa, peta). Kode SLS yang sama muncul di beberapa desa, jadi desa harus ikut di nama.

Berkas lama (awalan s<peta> tanpa desa) tetap milik desa 004 dan 005/000100 supaya hasil yang sudah ada tidak putus.
"""
import re
LEGACY = {("004", None), ("005", "000100")}

def tag_for(desa, mapname):
    clean = re.sub(r"\W", "", mapname)
    sls = clean[:6]
    if (desa, None) in LEGACY or (desa, sls) in LEGACY:
        return "s" + clean
    return f"s{desa}_{clean}"
