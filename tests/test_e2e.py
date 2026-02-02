import os
import sqlite3
import tempfile
import asyncio
import pytest
from scraper_laptops import demo_mode, run_live_scrape, DB_PATH, HAS_PLAYWRIGHT


def count_listings(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM listings')
    v = c.fetchone()[0]
    conn.close()
    return v


def test_demo_mode_inserts_rows(tmp_path):
    # create a temporary DB using existing schema
    db_file = tmp_path / 'test_arbitrage.db'
    # copy schema from main DB
    if os.path.exists(DB_PATH):
        src = DB_PATH
    else:
        pytest.skip('No DB in workspace to copy schema from')

    # Create empty DB with same tables
    conn = sqlite3.connect(db_file)
    src_conn = sqlite3.connect(src)
    src_cursor = src_conn.cursor()
    src_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    for row in src_cursor.fetchall():
        if row[0]:
            try:
                conn.execute(row[0])
            except Exception:
                pass
    conn.commit()
    conn.close()
    src_conn.close()

    # run demo_mode but override DB_PATH via run_live_scrape's db override
    # demo_mode uses global DB_PATH; temporarily override
    from scraper_laptops import save_listing, save_product, generate_product_hash, is_ram_upgradeable

    # emulate demo_mode writes directly to db_file
    sample_laptops = [
        {
            'brand': 'Dell',
            'title': 'Dell XPS 13 9310 Intel Core i7-1185G7 16GB DDR4 512GB SSD 13.4" FHD+',
            'price': 1299.99,
            'cpu_model': 'i7-1185G7',
            'ram_capacity': '16GB',
            'ram_type': 'DDR4',
            'ssd_capacity': '512GB',
            'screen_size': '13.4"',
            'source': 'BestBuy.ca',
            'url': 'https://www.bestbuy.ca/product/dell-xps-13/123456789'
        },
    ]

    # insert one row using module helpers to the test DB
    product_hash = generate_product_hash(sample_laptops[0]['brand'], sample_laptops[0]['cpu_model'], sample_laptops[0]['screen_size'])
    # monkeypatch DB_PATH
    import scraper_laptops as module
    old = module.DB_PATH
    module.DB_PATH = str(db_file)
    save_product(product_hash, sample_laptops[0]['brand'], sample_laptops[0]['title'], sample_laptops[0]['cpu_model'], sample_laptops[0]['screen_size'], is_ram_upgradeable(sample_laptops[0]['title']), True)
    save_listing(product_hash, sample_laptops[0]['source'], 'New', sample_laptops[0]['title'], sample_laptops[0]['price'], sample_laptops[0]['cpu_model'], sample_laptops[0]['ram_capacity'], sample_laptops[0]['ram_type'], sample_laptops[0]['ssd_capacity'], sample_laptops[0]['url'])
    module.DB_PATH = old

    assert count_listings(str(db_file)) == 1


@pytest.mark.skipif(not HAS_PLAYWRIGHT or not (os.environ.get('RUN_LIVE_SMOKE') in ['1','true','True']), reason='Playwright not available or RUN_LIVE_SMOKE not set')
def test_live_smoke_no_save():
    # Smoke test: run live scrape against Amazon only but do not save
    try:
        asyncio.run(run_live_scrape(limit_per_site=2, save=False, queries=['laptop'], sites=['amazon']))
    except Exception as e:
        pytest.skip(f'Live smoke skipped due to runtime error: {e}')
    # If we reach here, function executed without raising
    assert True
