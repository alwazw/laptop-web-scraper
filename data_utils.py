import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')

CONDITION_MARKDOWN = {
    'New': 1.0,
    'OpenBox': 0.9,
    'Refurbished Excellent': 0.85,
    'Refurbished Good': 0.75,
    'Refurbished Fair': 0.6,
    'Refurbished Other': 0.5
}

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def fetch_component_history():
    query = "SELECT report_date, component_key, avg_price FROM component_daily_avg ORDER BY report_date ASC"
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

def fetch_latest_listings():
    query = """
    SELECT l.*, p.brand, p.cpu_model, p.screen_size, p.is_ram_upgradeable, p.is_ssd_upgradeable
    FROM listings l
    JOIN products p ON l.product_hash = p.product_hash
    ORDER BY l.scraped_at DESC
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

def fetch_execution_logs():
    query = "SELECT * FROM execution_logs ORDER BY timestamp DESC LIMIT 50"
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

def get_latest_component_prices():
    query = """
    SELECT component_key, avg_price
    FROM component_daily_avg
    WHERE report_date = (SELECT MAX(report_date) FROM component_daily_avg)
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn)
    return dict(zip(df['component_key'], df['avg_price']))

def get_historical_baseline(product_hash, days=60):
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    query = """
    SELECT AVG(price) FROM listing_price_history
    WHERE product_hash = ? AND condition_tier = 'New' AND recorded_at > ?
    """
    with get_connection() as conn:
        res = conn.execute(query, (product_hash, cutoff)).fetchone()
        return res[0] if res and res[0] else None

def calculate_tev(listing_row, latest_components, historical_new_price):
    harvest_value = 0
    if listing_row['is_ram_upgradeable']:
        ram_key = f"RAM_{listing_row['ram_spec_type'] or 'DDR4'}_{listing_row['ram_spec_capacity'] or '8GB'}".replace(' ', '')
        harvest_value += latest_components.get(ram_key, 40.0)

    if listing_row['is_ssd_upgradeable']:
        ssd_key = f"SSD_NVMe_{listing_row['ssd_spec_capacity'] or '256GB'}".replace(' ', '')
        harvest_value += latest_components.get(ssd_key, 50.0)

    chassis_base = 150.0 if "i7" in str(listing_row['cpu_model']).lower() else 100.0
    harvest_total = harvest_value + chassis_base

    chassis_value = 0
    if historical_new_price:
        multiplier = CONDITION_MARKDOWN.get(listing_row['condition_tier'], 0.5)
        chassis_value = historical_new_price * multiplier
    else:
        # Fallback if no history: use listing price if it's 'New'
        if listing_row['condition_tier'] == 'New':
            chassis_value = listing_row['listing_price']
        else:
            chassis_value = harvest_total # Worst case

    return max(harvest_total, chassis_value)

def log_execution(scraper_name, status, items_found=0, error_message=None):
    query = "INSERT INTO execution_logs (scraper_name, status, items_found, error_message) VALUES (?, ?, ?, ?)"
    with get_connection() as conn:
        conn.execute(query, (scraper_name, status, items_found, error_message))
        conn.commit()

def get_db_stats():
    stats = {}
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM listings")
        stats['total_listings'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        stats['total_products'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT component_key) FROM component_daily_avg")
        stats['tracked_components'] = cursor.fetchone()[0]
    return stats
