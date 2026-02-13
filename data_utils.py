import sqlite3
import pandas as pd
from pathlib import Path
from contextlib import closing
from datetime import datetime, timedelta
import json

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
    with closing(get_connection()) as conn:
        return pd.read_sql_query(query, conn)

def fetch_latest_listings():
    # Use fallback for column names if needed, though db_setup should handle it
    query = """
    SELECT l.*, p.brand, p.cpu_model, p.cpu_gen, p.screen_size,
           p.is_ram_upgradeable, p.is_ssd_upgradeable, p.ram_soldered,
           p.ssd_soldered, p.gpu_dedicated, p.is_touchscreen
    FROM listings l
    JOIN products p ON l.product_hash = p.product_hash
    ORDER BY l.scraped_at DESC
    """
    with closing(get_connection()) as conn:
        df = pd.read_sql_query(query, conn)
        # Robustness check: Ensure condition_tier exists
        if 'condition_tier' not in df.columns and 'condition' in df.columns:
            df['condition_tier'] = df['condition']
        if 'listing_price' not in df.columns and 'price' in df.columns:
            df['listing_price'] = df['price']
        return df

def fetch_execution_logs():
    query = "SELECT * FROM execution_logs ORDER BY timestamp DESC LIMIT 100"
    with closing(get_connection()) as conn:
        return pd.read_sql_query(query, conn)

def get_latest_component_prices():
    query = """
    SELECT component_key, avg_price
    FROM component_daily_avg
    WHERE report_date = (SELECT MAX(report_date) FROM component_daily_avg)
    """
    with closing(get_connection()) as conn:
        df = pd.read_sql_query(query, conn)
    return dict(zip(df['component_key'], df['avg_price']))

def get_historical_baseline(product_hash, days=60):
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    query = """
    SELECT AVG(price) FROM listing_price_history
    WHERE product_hash = ? AND condition_tier = 'New' AND recorded_at > ?
    """
    with closing(get_connection()) as conn:
        res = conn.execute(query, (product_hash, cutoff)).fetchone()
        return res[0] if res and res[0] else None

def get_historical_avg(product_hash, days=30):
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    query = "SELECT AVG(price) FROM listing_price_history WHERE product_hash = ? AND recorded_at > ?"
    with closing(get_connection()) as conn:
        res = conn.execute(query, (product_hash, cutoff)).fetchone()
        return res[0] if res and res[0] else None

def calculate_triangulated_margin(buy_price, sell_price, market_ref_price, shipping_est=25.0):
    """
    Triangulated Profit Logic:
    Validation: If Sell_Price > Market_Ref_Price * 1.3, warn 'Price Inflated'.
    Calculation: Net_Margin = (Sell_Price * 0.85) - Buy_Price - Shipping_Est.
    """
    is_unrealistic = sell_price > (market_ref_price * 1.3)
    net_profit = (sell_price * 0.85) - buy_price - shipping_est
    margin_pct = (net_profit / buy_price * 100) if buy_price > 0 else 0
    return net_profit, margin_pct, is_unrealistic

def calculate_tev(listing_row, latest_components, historical_new_price):
    """
    Returns (tev, harvest_total, chassis_value)
    """
    # 1. Component Harvest Value
    harvest_value = 0
    if listing_row.get('is_ram_upgradeable', 1):
        ram_key = f"RAM_{listing_row.get('ram_spec_type') or 'DDR4'}_{listing_row.get('ram_spec_capacity') or '8GB'}".replace(' ', '')
        harvest_value += latest_components.get(ram_key, 40.0)

    if listing_row.get('is_ssd_upgradeable', 1):
        ssd_key = f"SSD_NVMe_{listing_row.get('ssd_spec_capacity') or '256GB'}".replace(' ', '')
        harvest_value += latest_components.get(ssd_key, 50.0)

    chassis_base = 150.0 if "i7" in str(listing_row.get('cpu_model', '')).lower() else 100.0
    harvest_total = harvest_value + chassis_base

    # 2. Condition-Adjusted Chassis Value
    chassis_value = 0
    condition = listing_row.get('condition_tier', 'New')
    if historical_new_price:
        multiplier = CONDITION_MARKDOWN.get(condition, 0.5)
        chassis_value = historical_new_price * multiplier
    else:
        if condition == 'New':
            chassis_value = listing_row.get('listing_price', 0)
        else:
            chassis_value = harvest_total # Safety floor

    tev = max(harvest_total, chassis_value)
    return tev, harvest_total, chassis_value

def log_execution(scraper_name, status, items_found=0, error_message=None, metadata=None):
    query = "INSERT INTO execution_logs (scraper_name, status, items_found, error_message, metadata) VALUES (?, ?, ?, ?, ?)"
    with closing(get_connection()) as conn:
        conn.execute(query, (scraper_name, status, items_found, error_message, json.dumps(metadata) if metadata else None))
        conn.commit()

def get_db_stats():
    stats = {}
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM listings")
        stats['total_listings'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        stats['total_products'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT component_key) FROM component_daily_avg")
        stats['tracked_components'] = cursor.fetchone()[0]

        # Data Freshness
        cursor.execute("SELECT MAX(scraped_at) FROM listings")
        res = cursor.fetchone()[0]
        stats['last_update'] = res if res else "N/A"

    return stats

def save_scraper_config(config_dict):
    with closing(get_connection()) as conn:
        conn.execute("INSERT OR REPLACE INTO scraper_config (config_key, config_value) VALUES ('default', ?)", (json.dumps(config_dict),))
        conn.commit()

def load_scraper_config():
    with closing(get_connection()) as conn:
        res = conn.execute("SELECT config_value FROM scraper_config WHERE config_key = 'default'").fetchone()
        if res:
            return json.loads(res[0])
    return None
