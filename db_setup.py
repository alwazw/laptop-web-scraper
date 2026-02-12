import sqlite3
import os
from datetime import datetime
from pathlib import Path

def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_database(force_reset=False):
    # Create database file inside `data/` directory
    db_path = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')
    os.makedirs(Path(db_path).parent, exist_ok=True)

    if force_reset and os.path.exists(db_path):
        os.remove(db_path)
        print("Database reset forced.")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Component Tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                subtype TEXT,
                capacity TEXT NOT NULL,
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
                component_key TEXT NOT NULL,
                avg_price REAL NOT NULL,
                UNIQUE(report_date, component_key)
            )
        ''')

        # 3. Product Catalog
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_hash TEXT PRIMARY KEY,
                brand TEXT,
                guessed_model TEXT,
                cpu_model TEXT,
                screen_size TEXT,
                is_ram_upgradeable INTEGER DEFAULT 1,
                is_ssd_upgradeable INTEGER DEFAULT 1
            )
        ''')

        # 4. Live Listings (v2.0 Schema)
        # We use a try block to handle migration from v1.0 if columns are missing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_hash TEXT,
                source TEXT,
                condition_tier TEXT,
                listing_title TEXT,
                listing_price REAL NOT NULL,
                cpu_spec TEXT,
                ram_spec_capacity TEXT,
                ram_spec_type TEXT,
                ram_speed TEXT,
                ssd_spec_capacity TEXT,
                ssd_architecture TEXT,
                seller_id TEXT,
                seller_rating REAL,
                fulfillment_type TEXT,
                url TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_hash) REFERENCES products(product_hash)
            )
        ''')

        # Check for missing columns in existing listings table (Migration Support)
        cursor.execute("PRAGMA table_info(listings)")
        columns = [col[1] for col in cursor.fetchall()]

        needed_columns = {
            'condition_tier': 'TEXT',
            'listing_price': 'REAL',
            'ram_speed': 'TEXT',
            'ssd_architecture': 'TEXT',
            'seller_id': 'TEXT',
            'seller_rating': 'REAL',
            'fulfillment_type': 'TEXT'
        }

        for col, dtype in needed_columns.items():
            if col not in columns:
                try:
                    cursor.execute(f"ALTER TABLE listings ADD COLUMN {col} {dtype}")
                    print(f"Migrated: Added column {col} to listings table.")
                except Exception as e:
                    print(f"Migration error for {col}: {e}")

        # 5. Price History
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
                strategy TEXT NOT NULL,
                product_hash TEXT,
                listing_id INTEGER,
                chosen_valuation_method TEXT,
                net_margin_pct REAL,
                confidence_score REAL,
                data_freshness_age INTEGER,
                status TEXT DEFAULT 'evaluated',
                FOREIGN KEY(product_hash) REFERENCES products(product_hash),
                FOREIGN KEY(listing_id) REFERENCES listings(id)
            )
        ''')

        # 7. Execution Logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                scraper_name TEXT,
                status TEXT,
                error_message TEXT,
                items_found INTEGER
            )
        ''')

        # 8. Scraper Configuration (New for v2.1)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraper_config (
                config_key TEXT PRIMARY KEY,
                config_value TEXT
            )
        ''')

        conn.commit()

    print(f"Enterprise Database initialized successfully at {db_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Force reset database')
    args = parser.parse_args()
    init_database(force_reset=args.reset)
