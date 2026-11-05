import sqlite3, sys, collections
c = sqlite3.connect(sys.argv[1])
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
rows = c.execute(f'select fid,no_bang,geotag_latitude,geotag_longitude,geotag_accuracy,count_usaha,ada_keluarga_value,unique_bang from "{t}"').fetchall()
print("rows", len(rows))
by = collections.defaultdict(list)
for r in rows:
    by[r[1]].append(r)
print("distinct no_bang", len(by))
print("no_bang dobel:", {k: len(v) for k, v in by.items() if len(v) > 1})
coords = collections.Counter((round(r[2], 6), round(r[3], 6)) for r in rows)
print("koordinat identik:", sum(1 for v in coords.values() if v > 1))
nums = sorted(int(k) for k in by if k and k.isdigit())
print("min/max", nums[0], nums[-1], "hilang:", [n for n in range(nums[0], nums[-1] + 1) if n not in set(nums)][:40])
