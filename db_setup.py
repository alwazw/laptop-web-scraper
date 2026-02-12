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

        # 1. Component Tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, -- 'RAM' or 'SSD'
                subtype TEXT, -- 'DDR4', 'DDR5', 'NVMe', 'SATA', 'MAC'
                capacity TEXT NOT NULL, -- '8GB', '1TB'
                price REAL NOT NULL,
                url TEXT,
                source TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Daily Averages for Components
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS component_daily_avg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE NOT NULL,
                component_key TEXT NOT NULL, -- e.g. 'RAM_DDR4_8GB'
                avg_price REAL NOT NULL,
                UNIQUE(report_date, component_key)
            )
        ''')

        # 3. Product Catalog (Hardware-Aware Hashing)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_hash TEXT PRIMARY KEY, -- SHA256(Brand+CPU+ScreenSize)
                brand TEXT,
                guessed_model TEXT,
                cpu_model TEXT,
                screen_size TEXT,
                is_ram_upgradeable INTEGER DEFAULT 1,
                is_ssd_upgradeable INTEGER DEFAULT 1
            )
        ''')

        # 4. Live Listings (v2.0 Expanded)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_hash TEXT,
                source TEXT, -- 'Amazon.ca', 'Walmart.ca', 'BestBuy.ca', etc.
                condition_tier TEXT, -- 'New', 'OpenBox', 'Refurbished Excellent', etc.
                listing_title TEXT,
                listing_price REAL NOT NULL,
                cpu_spec TEXT,
                ram_spec_capacity TEXT,
                ram_spec_type TEXT,
                ram_speed TEXT,
                ssd_spec_capacity TEXT,
                ssd_architecture TEXT, -- 'M2', 'SATA', 'MAC'
                seller_id TEXT,
                seller_rating REAL,
                fulfillment_type TEXT,
                url TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_hash) REFERENCES products(product_hash)
            )
        ''')

        # 5. Price History for Baseline Calculation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listing_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_hash TEXT,
                price REAL,
                condition_tier TEXT,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_hash) REFERENCES products(product_hash)
            )
        ''')

        # 6. Arbitrage Decision Log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS arbitrage_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                strategy TEXT NOT NULL, -- 'dropship' or 'inventory'
                product_hash TEXT,
                listing_id INTEGER,
                chosen_valuation_method TEXT, -- 'component' vs 'chassis'
                net_margin_pct REAL,
                confidence_score REAL,
                data_freshness_age INTEGER, -- Minutes since last scrape
                status TEXT DEFAULT 'evaluated', -- 'accepted', 'rejected'
                FOREIGN KEY(product_hash) REFERENCES products(product_hash),
                FOREIGN KEY(listing_id) REFERENCES listings(id)
            )
        ''')

        # 7. Execution Logs for Scraper Health
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                scraper_name TEXT,
                status TEXT, -- 'success', 'failure'
                error_message TEXT,
                items_found INTEGER
            )
        ''')

        conn.commit()

    print(f"v2.0 Database initialized successfully at {db_path}")

if __name__ == "__main__":
    init_database()
