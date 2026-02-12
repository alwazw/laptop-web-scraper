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

async def run_live_scrape(limit_per_site=None, save=True, queries=None, sites=None, proxies=None):
    from data_utils import load_scraper_config, log_execution
    config = load_scraper_config()
    if config:
        queries = queries or config.get('queries')
        sites = sites or config.get('sites')
        limit_per_site = limit_per_site or config.get('limit')

    queries = queries or ['laptop']
    sites = set([s.lower() for s in (sites or ['amazon', 'bestbuy', 'canadacomputers', 'walmart', 'staples', 'dell', 'hp'])])
    limit_per_site = limit_per_site or 10

    all_results = []
    execution_details = []

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

                site_methods = {
                    'amazon': scrape_amazon,
                    'bestbuy': scrape_bestbuy,
                    'canadacomputers': scrape_canadacomputers,
                    'walmart': scrape_walmart,
                    'staples': scrape_staples,
                    'dell': scrape_dell,
                    'hp': scrape_hp
                }

                for site in sites:
                    if site in site_methods:
                        try:
                            res = await site_methods[site](page, q, limit_per_site)
                            all_results.extend(res)
                            execution_details.append({'query': q, 'site': site, 'status': 'success', 'found': len(res)})
                        except Exception as se:
                            execution_details.append({'query': q, 'site': site, 'status': 'failure', 'error': str(se)})

                await browser.close()
            except Exception as e:
                print(f"Scrape failed for query {q}: {e}")
                manager.report_failure(proxy_to_use)
                execution_details.append({'query': q, 'status': 'critical_failure', 'error': str(e)})

    # deduplicate and filter
    unique = {r['url']: r for r in all_results if r.get('url')}.values()

    filtered_count = 0
    filter_stats = {'brand': 0, 'ram': 0, 'ssd': 0}

    for r in unique:
        brand = extract_brand_from_title(r['title'])
        r['product_hash'] = generate_product_hash(brand, r['cpu_model'], r['screen_size'])
        r['condition_tier'] = extract_condition_tier(r['title'], r['source'])

        # Apply Filters from config
        if config:
            if config.get('brands') and brand not in config['brands']:
                filter_stats['brand'] += 1
                continue

            if config.get('min_ram'):
                min_ram_val = int(re.sub(r'\D', '', config['min_ram']))
                ram_cap, _ = extract_ram_from_title(r['title'])
                if ram_cap:
                    try:
                        curr_ram_val = int(re.sub(r'\D', '', ram_cap))
                        if curr_ram_val < min_ram_val:
                            filter_stats['ram'] += 1
                            continue
                    except: pass

            if config.get('min_ssd'):
                def to_gb(s):
                    if not s: return 0
                    try:
                        val = int(re.sub(r'\D', '', s))
                        if 'TB' in s.upper(): val *= 1024
                        return val
                    except: return 0
                min_ssd_gb = to_gb(config['min_ssd'])
                ssd_cap = extract_ssd_from_title(r['title'])
                if ssd_cap:
                    if to_gb(ssd_cap) < min_ssd_gb:
                        filter_stats['ssd'] += 1
                        continue

        if save:
            save_product(r['product_hash'], brand, r['title'], r['cpu_model'], r['screen_size'], True, True)
            save_listing(r)
            filtered_count += 1

    # Update metadata with filter stats
    log_execution('scraper_laptops', 'success', filtered_count, metadata={
        'details': execution_details,
        'filters_applied': filter_stats,
        'total_scraped': len(unique)
    })

    print(f"v2.0 Scrape completed: {filtered_count} listings saved ({len(unique) - filtered_count} filtered).")

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
    url = f'https://www.walmart.ca/search?q={query.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div[data-item-id]', timeout=10000)
        items = await page.query_selector_all('div[data-item-id]')
        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('span[data-automation-id="product-title"]')
            price_el = await item.query_selector('span[data-automation-id="product-price"]')
            link_el = await item.query_selector('a[data-automation-id="product-anchor"]')
            if title_el and price_el and link_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await link_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': 'https://www.walmart.ca' + link,
                        'source': 'Walmart.ca', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

async def scrape_staples(page, query, limit):
    url = f'https://www.staples.ca/search?query={query.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div.product-thumbnail', timeout=10000)
        items = await page.query_selector_all('div.product-thumbnail')
        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('a.product-thumbnail__title')
            price_el = await item.query_selector('span.money')
            if title_el and price_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await title_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': 'https://www.staples.ca' + link,
                        'source': 'Staples.ca', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

async def scrape_dell(page, query, limit):
    # Dell often uses a search API or complex JS. Simple approach:
    url = f'https://www.dell.com/en-ca/search/{query.replace(" ", "%20")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('article.ps-stack', timeout=10000)
        items = await page.query_selector_all('article.ps-stack')
        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('h3 a')
            price_el = await item.query_selector('div.ps-dell-price')
            if title_el and price_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await title_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': 'https:' + link if link.startswith('//') else link,
                        'source': 'Dell.com', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

async def scrape_hp(page, query, limit):
    url = f'https://www.hp.com/ca-en/shop/catalogsearch/result/?q={query.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('li.product-item', timeout=10000)
        items = await page.query_selector_all('li.product-item')
        results = []
        for item in items:
            if len(results) >= limit: break
            title_el = await item.query_selector('a.product-item-link')
            price_el = await item.query_selector('span.price')
            if title_el and price_el:
                title = (await title_el.inner_text()).strip()
                price = parse_price(await price_el.inner_text())
                link = await title_el.get_attribute('href')
                if price:
                    results.append({
                        'title': title, 'price': price, 'url': link,
                        'source': 'HP.com', 'cpu_model': extract_cpu_from_title(title),
                        'ram_capacity': extract_ram_from_title(title)[0], 'ram_type': extract_ram_from_title(title)[1],
                        'ssd_capacity': extract_ssd_from_title(title), 'screen_size': extract_screen_from_title(title)
                    })
        return results
    except: return []

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
