import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
for r in c.execute("select table_name,data_type,srs_id from gpkg_contents"):
    print(r)
for (t,) in c.execute("select table_name from gpkg_contents where data_type='features'").fetchall():
    print(t, c.execute(f'select count(*) from "{t}"').fetchone())
    print([r[1:3] for r in c.execute(f'pragma table_info("{t}")')])
    for r in c.execute(f'select * from "{t}" limit 3'):
        print([x if not isinstance(x, bytes) else f"<blob {len(x)}>" for x in r])
