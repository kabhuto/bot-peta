import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
print(c.execute(f'select status_pindah,count(*) from "{t}" group by 1').fetchall())
for r in c.execute(f'select no_bang,status_pindah,jarak_pindah_m,geotag_accuracy,blob_id from "{t}" where jarak_pindah_m>45 order by jarak_pindah_m desc'):
    print(r)
