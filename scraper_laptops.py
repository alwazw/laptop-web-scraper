import re
import sqlite3
import hashlib
import argparse
import asyncio
from datetime import datetime
import random
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except Exception:
    async_playwright = None
    HAS_PLAYWRIGHT = False

# Optional stealth support
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except Exception:
    stealth_async = None
    HAS_STEALTH = False

# Configuration
DB_PATH = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')

# Small UA pool for randomization
UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
]

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Proxy rotation manager
class ProxyManager:
    def __init__(self, proxies=None):
        self.proxies = list(proxies or [])
        self.index = 0
        self.failures = {p: 0 for p in self.proxies}

    def has_proxies(self):
        return len(self.proxies) > 0

    def get_proxy(self):
        if not self.proxies:
            return None
        p = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        return p

    def report_failure(self, proxy):
        if not proxy: return
        self.failures[proxy] = self.failures.get(proxy, 0) + 1
        if self.failures[proxy] > 3:
            try: self.proxies.remove(proxy)
            except ValueError: pass

    def report_success(self, proxy):
        if not proxy: return
        self.failures[proxy] = 0

def parse_price(text):
    if not text: return None
    if any(word in text.lower() for word in ['capacity', 'capacities', 'option', 'options']):
        return None
    s = re.sub(r'[^\d\.]', '', (text or '').replace(',', ''))
    try:
        p = float(s)
        return p if p > 0 else None
    except Exception:
        return None

def generate_product_hash(brand, cpu_model, screen_size):
    key = f'{brand}_{cpu_model}_{screen_size}'.lower().strip()
    return hashlib.sha256(key.encode()).hexdigest()

def is_ram_upgradeable(description):
    """Determine RAM upgradeability based on description heuristics"""
    description_lower = description.lower()
    if any(word in description_lower for word in ['lpddr', 'soldered', 'onboard', 'unified']):
        return False
    return True

def extract_condition_tier(title, source):
    title_l = title.lower()
    if 'renewed' in title_l or 'refurbished' in title_l or 'certified' in title_l:
        if 'excellent' in title_l or 'geeksquad' in title_l:
            return 'Refurbished Excellent'
        if 'fair' in title_l or 'scratch' in title_l:
            return 'Refurbished Fair'
        return 'Refurbished Good'
    if 'open-box' in title_l or 'open box' in title_l or 'like new' in title_l:
        return 'OpenBox'
    return 'New'

def save_product(product_hash, brand, guessed_model, cpu_model, screen_size, is_ram_upgradeable, is_ssd_upgradeable):
    with get_connection() as conn:
        conn.execute('''
            INSERT OR IGNORE INTO products (product_hash, brand, guessed_model, cpu_model, screen_size, is_ram_upgradeable, is_ssd_upgradeable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (product_hash, brand, guessed_model, cpu_model, screen_size, int(is_ram_upgradeable), int(is_ssd_upgradeable)))
        conn.commit()

def save_listing(listing_data):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO listings (
                product_hash, source, condition_tier, listing_title, listing_price,
                cpu_spec, ram_spec_capacity, ram_spec_type, ram_speed,
                ssd_spec_capacity, ssd_architecture,
                seller_id, seller_rating, fulfillment_type, url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_data['product_hash'], listing_data['source'], listing_data['condition_tier'],
            listing_data['title'], listing_data['price'],
            listing_data['cpu_model'], listing_data['ram_capacity'], listing_data['ram_type'], listing_data.get('ram_speed'),
            listing_data['ssd_capacity'], listing_data.get('ssd_architecture'),
            listing_data.get('seller_id'), listing_data.get('seller_rating'), listing_data.get('fulfillment_type'),
            listing_data['url']
        ))

        # Log to history
        cursor.execute('''
            INSERT INTO listing_price_history (product_hash, price, condition_tier)
            VALUES (?, ?, ?)
        ''', (listing_data['product_hash'], listing_data['price'], listing_data['condition_tier']))
        conn.commit()

async def _init_stealth(context):
    if HAS_STEALTH and stealth_async:
        await stealth_async(context)
    else:
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

async def run_live_scrape(limit_per_site=10, save=True, queries=None, sites=None, proxies=None):
    queries = queries or ['laptop']
    sites = set([s.lower() for s in (sites or ['amazon', 'bestbuy', 'canadacomputers', 'walmart', 'staples', 'dell', 'hp'])])

    all_results = []

    async with async_playwright() as p:
        manager = ProxyManager(proxies)

        for q in queries:
            proxy_to_use = manager.get_proxy()
            launch_kwargs = {'headless': True}
            if proxy_to_use: launch_kwargs['proxy'] = {'server': proxy_to_use}

            try:
                browser = await p.chromium.launch(**launch_kwargs)
                context = await browser.new_context(user_agent=random.choice(UA_POOL), locale='en-CA', timezone_id='America/Toronto')
                await _init_stealth(context)
                page = await context.new_page()

                if 'amazon' in sites:
                    all_results.extend(await scrape_amazon(page, q, limit_per_site))
                if 'bestbuy' in sites:
                    all_results.extend(await scrape_bestbuy(page, q, limit_per_site))
                if 'canadacomputers' in sites:
                    all_results.extend(await scrape_canadacomputers(page, q, limit_per_site))
                if 'walmart' in sites:
                    all_results.extend(await scrape_walmart(page, q, limit_per_site))
                if 'staples' in sites:
                    all_results.extend(await scrape_staples(page, q, limit_per_site))
                if 'dell' in sites:
                    all_results.extend(await scrape_dell(page, q, limit_per_site))
                if 'hp' in sites:
                    all_results.extend(await scrape_hp(page, q, limit_per_site))

                await browser.close()
            except Exception as e:
                print(f"Scrape failed for query {q}: {e}")
                manager.report_failure(proxy_to_use)

    # deduplicate
    unique = {r['url']: r for r in all_results if r.get('url')}.values()

    for r in unique:
        brand = extract_brand_from_title(r['title'])
        r['product_hash'] = generate_product_hash(brand, r['cpu_model'], r['screen_size'])
        r['condition_tier'] = extract_condition_tier(r['title'], r['source'])

        if save:
            save_product(r['product_hash'], brand, r['title'], r['cpu_model'], r['screen_size'], True, True)
            save_listing(r)

    print(f"v2.0 Scrape completed: {len(unique)} listings saved.")

def demo_mode():
    print('Starting laptop scraping (demo mode)...')
    sample_laptops = [
        {
            'title': 'Dell XPS 13 9310 Intel Core i7-1185G7 16GB DDR4 512GB SSD 13.4" FHD+',
            'price': 1299.99,
            'cpu_model': 'i7-1185G7',
            'ram_capacity': '16GB',
            'ram_type': 'DDR4',
            'ssd_capacity': '512GB',
            'screen_size': '13.4"',
            'source': 'BestBuy.ca',
            'url': 'https://www.bestbuy.ca/product/dell-xps-13/123456789',
            'condition_tier': 'New'
        },
        {
            'title': 'Apple MacBook Pro 14 M3 Pro 18GB 512GB SSD 14"',
            'price': 2499.99,
            'cpu_model': 'M3 Pro',
            'ram_capacity': '18GB',
            'ram_type': 'Unified',
            'ssd_capacity': '512GB',
            'screen_size': '14"',
            'source': 'Amazon.ca',
            'url': 'https://www.amazon.ca/macbook-pro-14-m3/987654321',
            'condition_tier': 'New'
        },
        {
            'title': 'Lenovo ThinkPad T14 Gen 3 Refurbished Good',
            'price': 899.99,
            'cpu_model': 'Ryzen 7 5800U',
            'ram_capacity': '16GB',
            'ram_type': 'DDR4',
            'ssd_capacity': '512GB',
            'screen_size': '14"',
            'source': 'Walmart.ca',
            'url': 'https://www.walmart.ca/en/ip/lenovo-thinkpad/555',
            'condition_tier': 'Refurbished Good'
        },
        {
            'title': 'Lenovo ThinkPad T14 Gen 3 (High Price)',
            'price': 1199.99,
            'cpu_model': 'Ryzen 7 5800U',
            'ram_capacity': '16GB',
            'ram_type': 'DDR4',
            'ssd_capacity': '512GB',
            'screen_size': '14"',
            'source': 'Amazon.ca',
            'url': 'https://www.amazon.ca/lenovo-thinkpad-expensive/123',
            'condition_tier': 'New'
        }
    ]

    for r in sample_laptops:
        brand = extract_brand_from_title(r['title'])
        r['product_hash'] = generate_product_hash(brand, r['cpu_model'], r['screen_size'])
        save_product(r['product_hash'], brand, r['title'], r['cpu_model'], r['screen_size'], True, True)
        save_listing(r)
        print(f"Saved: {r['title'][:60]}")

    print('Laptop demo scraping completed.')

# --- Scraper Implementations ---

async def scrape_amazon(page, query, limit):
    url = f'https://www.amazon.ca/s?k={query.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        # Fallback selectors
        selectors = ['div[data-component-type="s-search-result"]', 'div.s-result-item']
        found = False
        for s in selectors:
            try:
                await page.wait_for_selector(s, timeout=5000)
                found = True
                break
            except: continue

        if not found: return []

        items = await page.query_selector_all('div[data-component-type="s-search-result"]')
        if not items: items = await page.query_selector_all('div.s-result-item')

        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('h2 a span')
            price_el = await item.query_selector('span.a-offscreen')
            link_el = await item.query_selector('h2 a')
            if title_el and price_el and link_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await link_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': 'https://www.amazon.ca' + link,
                        'source': 'Amazon.ca', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

async def scrape_bestbuy(page, query, limit):
    url = f'https://www.bestbuy.ca/en-ca/search?search={query.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div.productItem', timeout=10000)
        items = await page.query_selector_all('div.productItem')
        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('h3 a span') or await item.query_selector('div.productItemName_3PByU')
            price_el = await item.query_selector('div.price_2769_') or await item.query_selector('span.screenReaderOnly_2zX9X')
            link_el = await item.query_selector('h3 a') or await item.query_selector('a.link_3WP9K')
            if title_el and price_el and link_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await link_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': 'https://www.bestbuy.ca' + link,
                        'source': 'BestBuy.ca', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

async def scrape_canadacomputers(page, query, limit):
    url = f'https://www.canadacomputers.com/search/results_details.php?language=en&search={query.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div.product', timeout=10000)
        items = await page.query_selector_all('div.product')
        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('a.productName')
            price_el = await item.query_selector('span.price')
            if title_el and price_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await title_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': 'https://www.canadacomputers.com/' + link.lstrip('/'),
                        'source': 'CanadaComputers.ca', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

async def scrape_walmart(page, query, limit):
    return []

async def scrape_staples(page, query, limit):
    return []

async def scrape_dell(page, query, limit):
    return []

async def scrape_hp(page, query, limit):
    return []

# --- Parsers ---

def extract_brand_from_title(title):
    brands = ['Dell', 'HP', 'Apple', 'Lenovo', 'Acer', 'Asus', 'Microsoft', 'Samsung', 'MSI', 'Razer']
    for b in brands:
        if b.lower() in title.lower(): return b
    return 'Generic'

def extract_cpu_from_title(title):
    m = re.search(r'([iI]\s?\d-[\w\d-]+|M\d\s?Pro|Ryzen\s?\d+\s?\w+|Celeron\s?\w+|Athlon\s?\w+)', title, re.I)
    return m.group(0) if m else 'Unknown'

def extract_ram_from_title(title):
    m = re.search(r'(\d+GB)\s*(DDR\d|Unified)?', title, re.I)
    return (m.group(1), m.group(2)) if m else (None, None)

def extract_ssd_from_title(title):
    m = re.search(r'(\d+(?:GB|TB))\s*(?:SSD|nvme|SSD NVMe)', title, re.I)
    return m.group(1) if m else None

def extract_screen_from_title(title):
    m = re.search(r'(\d{1,2}(?:\.\d)?\")', title)
    return m.group(0) if m else '15.6"'

# --- Main ---

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['demo', 'live'], default='demo')
    args = parser.parse_args()
    if args.mode == 'demo':
        demo_mode()
    else:
        asyncio.run(run_live_scrape())

if __name__ == '__main__':
    main()
