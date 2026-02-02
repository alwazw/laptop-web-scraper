import sqlite3, os, sys

from pathlib import Path

db = str(Path(__file__).resolve().parents[1] / 'data' / 'arbitrage.db')
if not os.path.exists(db):
    print("ERROR: DB file not found:", db)
    sys.exit(2)

conn = sqlite3.connect(db)
c = conn.cursor()
# list tables
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
for t in tables:
    print('\n-- TABLE:', t, '--')
    try:
        # print schema
        c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,))
        schema = c.fetchone()
        print('Schema:', schema[0] if schema and schema[0] else 'N/A')
        # print first 5 rows
        c.execute(f"SELECT * FROM {t} LIMIT 5")
        rows = c.fetchall()
        if rows:
            # print column names
            col_names = [d[0] for d in c.description]
            print('Columns:', col_names)
            for r in rows:
                print(r)
        else:
            print('(no rows)')
    except Exception as e:
        print('Error reading table', t, e)

conn.close()
