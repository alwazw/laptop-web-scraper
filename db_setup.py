import sqlite3
import os
from datetime import datetime
from pathlib import Path

def init_database():
    # Create database file inside `data/` directory
    db_path = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')
    os.makedirs(Path(db_path).parent, exist_ok=True)

    # Connect to database
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Create components_tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, -- 'RAM' or 'SSD'
                subtype TEXT, -- 'DDR4', 'DDR5', 'NVMe'
                capacity TEXT NOT NULL, -- '8GB', '1TB'
                price REAL NOT NULL,
                url TEXT,
                source TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create component_daily_avg table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS component_daily_avg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE NOT NULL,
                component_key TEXT NOT NULL, -- e.g. 'RAM_DDR4_8GB'
                avg_price REAL NOT NULL,
                UNIQUE(report_date, component_key)
            )
        ''')

        # Create products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_hash TEXT PRIMARY KEY, -- Hash of Brand+CPU+Screen
                brand TEXT,
                guessed_model TEXT,
                cpu_model TEXT,
                screen_size TEXT,
                is_ram_upgradeable INTEGER DEFAULT 1, -- 1 for Yes, 0 for No
                is_ssd_upgradeable INTEGER DEFAULT 1
            )
        ''')

        # Create listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_hash TEXT,
                source TEXT, -- 'BestBuy', 'Amazon', 'CanadaComputers'
                condition TEXT, -- 'New', 'OpenBox', 'Refurb'
                listing_title TEXT,
                listing_price REAL NOT NULL,
                cpu_spec TEXT,
                ram_spec_capacity TEXT, -- '16GB'
                ram_spec_type TEXT, -- 'DDR4' or 'DDR5'
                ssd_spec_capacity TEXT, -- '512GB'
                url TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_hash) REFERENCES products(product_hash)
            )
        ''')

        # Commit changes
        conn.commit()

    print(f"Database initialized successfully at {db_path}")
    print("All tables created with the exact schema specified.")

if __name__ == "__main__":
    init_database()
