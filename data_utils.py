import sqlite3
import pandas as pd
from pathlib import Path
import os

DB_PATH = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def fetch_component_history():
    query = "SELECT report_date, component_key, avg_price FROM component_daily_avg ORDER BY report_date ASC"
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

def fetch_latest_listings():
    query = """
    SELECT l.listing_title, l.listing_price, l.source, l.condition, l.cpu_spec,
           l.ram_spec_capacity, l.ram_spec_type, l.ssd_spec_capacity, l.url, l.scraped_at,
           p.brand, p.cpu_model, p.screen_size, p.is_ram_upgradeable, p.is_ssd_upgradeable
    FROM listings l
    JOIN products p ON l.product_hash = p.product_hash
    ORDER BY l.scraped_at DESC
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

def get_latest_component_prices():
    """Returns a dict of latest prices for components to calculate 'scrap value'"""
    query = """
    SELECT component_key, avg_price
    FROM component_daily_avg
    WHERE report_date = (SELECT MAX(report_date) FROM component_daily_avg)
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn)
    return dict(zip(df['component_key'], df['avg_price']))

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
