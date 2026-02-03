# Database Schema

```sql
CREATE TABLE IF NOT EXISTS components_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, -- 'RAM' or 'SSD'
    subtype TEXT, -- 'DDR4', 'NVMe'
    capacity TEXT NOT NULL,
    price REAL NOT NULL,
    url TEXT,
    source TEXT,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS component_daily_avg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE NOT NULL,
    component_key TEXT NOT NULL, -- e.g. 'RAM_DDR4_8GB'
    avg_price REAL NOT NULL,
    UNIQUE(report_date, component_key)
);

CREATE TABLE IF NOT EXISTS products (
    product_hash TEXT PRIMARY KEY, -- Hash of Brand+CPU+Screen
    brand TEXT,
    guessed_model TEXT,
    cpu_model TEXT,
    screen_size TEXT,
    is_ram_upgradeable INTEGER DEFAULT 1, -- 1 for Yes, 0 for No
    is_ssd_upgradeable INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_hash TEXT,
    source TEXT, -- 'BestBuy', 'Amazon'
    condition TEXT, -- 'New', 'Refurb'
    listing_title TEXT,
    listing_price REAL NOT NULL,
    cpu_spec TEXT,
    ram_spec_capacity TEXT, -- '16GB'
    ram_spec_type TEXT, -- 'DDR4'
    ssd_spec_capacity TEXT, -- '512GB'
    url TEXT,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_hash) REFERENCES products(product_hash)
);
```