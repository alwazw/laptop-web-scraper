import sqlite3
import os

from pathlib import Path
DB = str(Path(__file__).resolve().parents[1] / 'data' / 'arbitrage.db')
if not os.path.exists(DB):
    print("DB not found:", DB)
    raise SystemExit(1)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Known demo titles (from scraper_laptops.py)
demo_titles = [
    'Dell XPS 13 9310 Intel Core i7-1185G7 16GB DDR4 512GB SSD 13.4" FHD+',
    'Apple MacBook Pro 14 M3 Pro 18GB 512GB SSD 14"',
    'Lenovo ThinkPad T14 Gen 3 AMD Ryzen 7 5800U 16GB DDR4 512GB SSD 14" FHD'
]

# Delete listings matching demo titles
for t in demo_titles:
    print(f"Removing listings that match title: {t}")
    c.execute("DELETE FROM listings WHERE listing_title = ?", (t,))

# Delete products that no longer have listings
c.execute("DELETE FROM products WHERE product_hash NOT IN (SELECT DISTINCT product_hash FROM listings)")

conn.commit()

# Show counts
c.execute("SELECT COUNT(*) FROM listings")
print('Listings remaining:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM products")
print('Products remaining:', c.fetchone()[0])

conn.close()
