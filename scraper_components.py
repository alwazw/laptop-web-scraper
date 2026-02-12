import asyncio
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import hashlib
from data_utils import get_connection, log_execution

async def scrape_amazon_ca(page, search_term):
    """Scrape Amazon.ca for lowest 3 valid prices"""
    try:
        await page.goto(f'https://www.amazon.ca/s?k={search_term.replace(" ", "+")}', timeout=30000)
        if "Something Went Wrong" in await page.content():
             return []
        try:
            await page.wait_for_selector('div.s-result-item, div[data-component-type="s-search-result"]', timeout=15000)
        except Exception as e:
            return []

        items = await page.query_selector_all('div[data-component-type="s-search-result"]')
        if not items: items = await page.query_selector_all('div.s-result-item')

        results = []
        for item in items[:25]:
            try:
                sponsored = await item.query_selector('span.a-color-secondary')
                if sponsored:
                    text = await sponsored.inner_text()
                    if 'Sponsored' in text or 'Promoted' in text: continue

                price = None
                offscreen = await item.query_selector('span.a-offscreen')
                if offscreen:
                    txt = await offscreen.inner_text()
                    if '$' in txt and 'capacity' not in txt.lower():
                        price_match = re.search(r'\d+(\.\d+)?', txt.replace(',', ''))
                        if price_match: price = float(price_match.group(0))

                if not price:
                    price_elem = await item.query_selector('span.a-price-whole')
                    if price_elem:
                        price_text = await price_elem.inner_text()
                        price_match = re.search(r'(\d+,)?\d+', price_text.replace(',', ''))
                        if price_match: price = float(price_match.group(0))

                if price and price > 0:
                    results.append({
                        'price': price,
                        'source': 'Amazon.ca',
                        'url': f'https://www.amazon.ca/s?k={search_term.replace(" ", "+")}'
                    })
            except Exception: continue
        return sorted(results, key=lambda x: x['price'])[:3]
    except Exception as e:
        print(f'Error scraping Amazon.ca for {search_term}: {e}')
        return []

async def scrape_newegg_ca(page, search_term):
    """Scrape Newegg.ca for lowest 3 valid prices"""
    try:
        await page.goto(f'https://www.newegg.ca/p/pl?d={search_term.replace(" ", "+")}', timeout=30000)
        await page.wait_for_selector('div.item-cell', timeout=30000)
        items = await page.query_selector_all('div.item-cell')

        results = []
        for item in items[:20]:
            try:
                sponsored = await item.query_selector('div.ad-badge')
                if sponsored: continue
                price_elem = await item.query_selector('li.price-current strong')
                if price_elem:
                    price_text = await price_elem.inner_text()
                    price_match = re.search(r'(\d+,)?\d+\.\d+', price_text)
                    if price_match:
                        price = float(price_match.group(0).replace(',', ''))
                        if price > 0:
                            results.append({
                                'price': price,
                                'source': 'Newegg.ca',
                                'url': f'https://www.newegg.ca/p/pl?d={search_term.replace(" ", "+")}'
                            })
            except Exception: continue
        return sorted(results, key=lambda x: x['price'])[:3]
    except Exception as e:
        print(f'Error scraping Newegg.ca for {search_term}: {e}')
        return []

async def save_component_data(component_type, subtype, capacity, price, url, source):
    with get_connection() as conn:
        conn.execute('''
            INSERT INTO components_tracking (type, subtype, capacity, price, url, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (component_type, subtype, capacity, price, url, source))
        conn.commit()

async def save_daily_avg(component_key, avg_price):
    with get_connection() as conn:
        today = datetime.now().strftime('%Y-%m-%d')
        conn.execute('''
            INSERT OR REPLACE INTO component_daily_avg (report_date, component_key, avg_price)
            VALUES (?, ?, ?)
        ''', (today, component_key, avg_price))
        conn.commit()

async def scrape_components():
    print('Starting v2.0 component scraping...')
    ram_targets = [('RAM', 'DDR4', '8GB'), ('RAM', 'DDR4', '16GB'), ('RAM', 'DDR5', '16GB'), ('RAM', 'DDR5', '32GB')]
    ssd_targets = [('SSD', 'NVMe', '512GB'), ('SSD', 'NVMe', '1TB'), ('SSD', 'NVMe', '2TB')]
    all_targets = ram_targets + ssd_targets

    items_processed = 0
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            for component_type, subtype, capacity in all_targets:
                search_term = f'{capacity} {subtype} Laptop RAM' if component_type == 'RAM' else f'{capacity} NVMe SSD laptop'
                results = await scrape_amazon_ca(page, search_term)
                if len(results) < 3:
                    results.extend(await scrape_newegg_ca(page, search_term))

                if results:
                    top_3 = sorted(results, key=lambda x: x['price'])[:3]
                    avg_price = sum(r['price'] for r in top_3) / len(top_3)
                    for r in top_3:
                        await save_component_data(component_type, subtype, capacity, r['price'], r['url'], r['source'])
                    await save_daily_avg(f'{component_type}_{subtype}_{capacity}', avg_price)
                    items_processed += 1
            await browser.close()
        log_execution('scraper_components', 'success', items_processed)
    except Exception as e:
        log_execution('scraper_components', 'failure', error_message=str(e))
    print('Component scraping completed.')

if __name__ == '__main__':
    asyncio.run(scrape_components())
