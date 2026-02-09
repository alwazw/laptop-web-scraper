import re
import sqlite3
import hashlib
import argparse
import asyncio
from datetime import datetime
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

from pathlib import Path
# Configuration
DB_PATH = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')

# Small UA pool for randomization
UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
]

# Proxy rotation manager
class ProxyManager:
    """Simple round-robin proxy manager with basic health marking."""
    def __init__(self, proxies=None):
        self.proxies = list(proxies or [])
        self.index = 0
        # failure counts
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
        if not proxy:
            return
        self.failures[proxy] = self.failures.get(proxy, 0) + 1
        # If a proxy fails more than 3 times, remove it from rotation
        if self.failures[proxy] > 3:
            try:
                self.proxies.remove(proxy)
            except ValueError:
                pass

    def report_success(self, proxy):
        if not proxy:
            return
        self.failures[proxy] = 0

# Helper: normalize price text
def parse_price(text):
    if not text:
        return None
    # Basic validation: should not contain "capacity" or "option"
    if any(word in text.lower() for word in ['capacity', 'capacities', 'option', 'options']):
        return None
    s = re.sub(r'[^\d\.]', '', (text or '').replace(',', ''))
    try:
        p = float(s)
        return p if p > 0 else None
    except Exception:
        return None


def generate_product_hash(brand, cpu_model, screen_size):
    """Generate SHA256 hash for product identification"""
    key = f'{brand}_{cpu_model}_{screen_size}'
    return hashlib.sha256(key.encode()).hexdigest()

def is_ram_upgradeable(description):
    """Determine RAM upgradeability based on description heuristics"""
    description_lower = description.lower()
    if any(word in description_lower for word in ['lpddr', 'soldered', 'onboard', 'unified']):
        return False
    return True

def save_product(product_hash, brand, guessed_model, cpu_model, screen_size, is_ram_upgradeable, is_ssd_upgradeable):
    """Save product to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO products (product_hash, brand, guessed_model, cpu_model, screen_size, is_ram_upgradeable, is_ssd_upgradeable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (product_hash, brand, guessed_model, cpu_model, screen_size, int(is_ram_upgradeable), int(is_ssd_upgradeable)))
        conn.commit()
    except Exception as e:
        print(f'Error saving product: {e}')
    finally:
        conn.close()

def save_listing(product_hash, source, condition, listing_title, listing_price, cpu_spec, ram_spec_capacity, ram_spec_type, ssd_spec_capacity, url):
    """Save listing to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO listings (product_hash, source, condition, listing_title, listing_price, cpu_spec, ram_spec_capacity, ram_spec_type, ssd_spec_capacity, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_hash, source, condition, listing_title, listing_price, cpu_spec, ram_spec_capacity, ram_spec_type, ssd_spec_capacity, url))
        conn.commit()
    except Exception as e:
        print(f'Error saving listing: {e}')
    finally:
        conn.close()

# --- Demo data routine ---

def demo_mode():
    print('Starting laptop scraping (demo mode)...')

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
        {
            'brand': 'Apple',
            'title': 'Apple MacBook Pro 14 M3 Pro 18GB 512GB SSD 14"',
            'price': 2499.99,
            'cpu_model': 'M3 Pro',
            'ram_capacity': '18GB',
            'ram_type': 'Unified',
            'ssd_capacity': '512GB',
            'screen_size': '14"',
            'source': 'Amazon.ca',
            'url': 'https://www.amazon.ca/macbook-pro-14-m3/987654321'
        },
        {
            'brand': 'Lenovo',
            'title': 'Lenovo ThinkPad T14 Gen 3 AMD Ryzen 7 5800U 16GB DDR4 512GB SSD 14" FHD',
            'price': 1199.99,
            'cpu_model': 'Ryzen 7 5800U',
            'ram_capacity': '16GB',
            'ram_type': 'DDR4',
            'ssd_capacity': '512GB',
            'screen_size': '14"',
            'source': 'CanadaComputers',
            'url': 'https://www.canadacomputers.com/product_info.php?cPath=7_15&item_id=123456'
        }
    ]

    for laptop in sample_laptops:
        product_hash = generate_product_hash(laptop['brand'], laptop['cpu_model'], laptop['screen_size'])
        save_product(product_hash, laptop['brand'], laptop['title'], laptop['cpu_model'], laptop['screen_size'], is_ram_upgradeable(laptop['title']), True)
        save_listing(product_hash, laptop['source'], 'New', laptop['title'], laptop['price'], laptop['cpu_model'], laptop['ram_capacity'], laptop['ram_type'], laptop['ssd_capacity'], laptop['url'])
        print(f"Saved: {laptop['title'][:60]} (${laptop['price']})")

    print('Laptop demo scraping completed.')


# --- Live scraping implementation ---

async def _init_stealth(context, level='basic'):
    """Initialize stealth settings.
    level: 'basic' | 'aggressive' — 'aggressive' applies more headers, timezone/locale, and user-agent randomization.
    """
    # Use playwright-stealth if available
    if HAS_STEALTH and stealth_async:
        try:
            await stealth_async(context)
            return
        except Exception:
            pass

    # Fallback: minimal stealth tweaks
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = {runtime: {}};
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        """
    )

    # Aggressive tweaks (set locale/timezone via context options elsewhere and set headers)
    if level == 'aggressive':
        try:
            await context.set_extra_http_headers({'Accept-Language':'en-CA,en;q=0.9'})
        except Exception:
            pass


async def run_live_scrape(limit_per_site=10, save=True, queries=None, sites=None, proxies=None, rotate_proxies=False, randomize_ua=False, stealth_level='basic', db_path=None, proxy_attempts=None):
    """Run live scrapes.
    - proxies: list of proxy servers (e.g. ['http://ip:port', 'http://ip2:port'])
    - rotate_proxies: if True rotate proxies per query
    - randomize_ua: if True pick random UA from UA_POOL per context
    - stealth_level: 'basic' or 'aggressive'
    - db_path: override DB_PATH for tests/dry runs
    """
    queries = queries or ['laptop', 'laptop 14"', 'laptop 13.4"']
    sites = set([s.lower() for s in (sites or ['amazon', 'bestbuy', 'canadacomputers'])])
    proxies = proxies or []

    # allow overriding DB for tests
    global DB_PATH
    old_db = DB_PATH
    if db_path:
        DB_PATH = db_path

    async with async_playwright() as p:
        all_results = []
        manager = ProxyManager(proxies)

        for idx, q in enumerate(queries):
            q = q.strip()
            attempts = 0
            max_attempts = proxy_attempts or (len(proxies) if proxies else 1)
            last_exception = None

            while attempts < max_attempts:
                attempts += 1
                proxy_to_use = None
                if manager.has_proxies():
                    if rotate_proxies:
                        proxy_to_use = manager.get_proxy()
                    else:
                        proxy_to_use = manager.proxies[0]

                launch_kwargs = {}
                if proxy_to_use:
                    launch_kwargs['proxy'] = {'server': proxy_to_use}

                try:
                    browser = await p.chromium.launch(headless=True, **launch_kwargs)

                    ua = UA_POOL[0]
                    if randomize_ua:
                        import random
                        ua = random.choice(UA_POOL)

                    context_kwargs = dict(user_agent=ua, viewport={'width': 1920, 'height': 1080})
                    if stealth_level == 'aggressive':
                        context_kwargs['locale'] = 'en-CA'
                        context_kwargs['timezone_id'] = 'America/Toronto'

                    context = await browser.new_context(**context_kwargs)
                    await _init_stealth(context, level=stealth_level)
                    page = await context.new_page()

                    # per-site scraping
                    page_results = []
                    if 'amazon' in sites:
                        try:
                            res = await scrape_amazon(page, q, limit_per_site)
                        except Exception as e:
                            print('Amazon error:', e)
                            res = []
                        page_results.extend(res)

                    if 'bestbuy' in sites:
                        try:
                            res = await scrape_bestbuy(page, q, limit_per_site)
                        except Exception as e:
                            print('BestBuy error:', e)
                            res = []
                        page_results.extend(res)

                    if 'canadacomputers' in sites:
                        try:
                            res = await scrape_canadacomputers(page, q, limit_per_site)
                        except Exception as e:
                            print('CanadaComputers error:', e)
                            res = []
                        page_results.extend(res)

                    # success for this attempt
                    manager.report_success(proxy_to_use)
                    all_results.extend(page_results)

                    await context.close()
                    await browser.close()
                    break

                except Exception as e:
                    last_exception = e
                    print(f'Attempt {attempts} for query "{q}" failed using proxy {proxy_to_use}: {e}')
                    manager.report_failure(proxy_to_use)
                    try:
                        await context.close()
                    except Exception:
                        pass
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    # if no proxies left, stop retrying
                    if not manager.has_proxies():
                        break
                    continue

            if attempts >= max_attempts and last_exception:
                print(f'All proxy attempts failed for query "{q}": {last_exception}')
                # continue to next query
                continue
        # Deduplicate by normalized URL or title+price
        unique = {}
        for r in all_results:
            url = r.get('url') or ''
            key = url.split('?')[0].rstrip('/') if url else (r.get('title'), r.get('price'))
            if key and key not in unique:
                unique[key] = r

        for r in unique.values():
            src = r.get('source', 'unknown')
            brand = extract_brand_from_title(r.get('title', ''))
            product_hash = generate_product_hash(brand, r.get('cpu_model') or '', r.get('screen_size') or '')
            save_product(product_hash, brand, r.get('title'), r.get('cpu_model') or '', r.get('screen_size') or '', is_ram_upgradeable(r.get('title')), True)
            if save:
                save_listing(product_hash, src, 'New', r.get('title'), r.get('price'), r.get('cpu_model'), r.get('ram_capacity'), r.get('ram_type'), r.get('ssd_capacity'), r.get('url'))

        # restore DB_PATH
        DB_PATH = old_db

        print(f'Live scrape completed: saved {len(unique)} unique listings')


# --- Site scrapers (called from run_live_scrape) ---
# Implementations are in this module to keep behavior explicit

async def scrape_amazon(page, search_term, limit=10):
    url = f'https://www.amazon.ca/s?k={search_term.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=15000)
        items = await page.query_selector_all('div[data-component-type="s-search-result"]')
        results = []
        for item in items:
            if len(results) >= limit:
                break
            try:
                sponsored = await item.query_selector('span.a-color-secondary')
                if sponsored:
                    text = (await sponsored.inner_text()) or ''
                    if 'Sponsored' in text or 'Promoted' in text:
                        continue

                title_el = await item.query_selector('h2 a span') or await item.query_selector('h2 span') or await item.query_selector('h2 a')
                if not title_el:
                    continue
                title = (await title_el.inner_text()).strip()
                link_el = await item.query_selector('h2 a') or await item.query_selector('a[href*="/dp/"]')
                url = await link_el.get_attribute('href') if link_el else None
                if url and url.startswith('/'):
                    url = 'https://www.amazon.ca' + url

                # Price extraction (prefer a-offscreen which contains full price)
                price = None
                price_el = await item.query_selector('span.a-offscreen')
                if price_el:
                    price = parse_price(await price_el.inner_text())
                if price is None:
                    # fallback: split whole/fraction
                    price_whole = await item.query_selector('span.a-price-whole')
                    price_frac = await item.query_selector('span.a-price-fraction')
                    if price_whole:
                        whole = (await price_whole.inner_text()).replace(',', '')
                        frac = (await price_frac.inner_text()).replace(',', '') if price_frac else '0'
                        price = parse_price(f"{whole}.{frac}")

                if price is None or price <= 0:
                    continue

                cpu = extract_cpu_from_title(title)
                ram_cap, ram_type = extract_ram_from_title(title)
                ssd = extract_ssd_from_title(title)
                screen = extract_screen_from_title(title)

                results.append({
                    'title': title,
                    'price': price,
                    'cpu_model': cpu,
                    'ram_capacity': ram_cap,
                    'ram_type': ram_type,
                    'ssd_capacity': ssd,
                    'screen_size': screen,
                    'url': url,
                    'source': 'Amazon.ca'
                })
            except Exception:
                continue
        return results
    except Exception as e:
        print(f'Amazon scrape error for "{search_term}": {e}')
        return []


async def scrape_bestbuy(page, search_term, limit=10):
    url = f'https://www.bestbuy.ca/en-ca/search?search={search_term.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div.productItem', timeout=15000)
        items = await page.query_selector_all('div.productItem')
        results = []
        for item in items:
            if len(results) >= limit:
                break
            try:
                badge = await item.query_selector('span.badge')
                if badge:
                    txt = (await badge.inner_text()) or ''
                    if 'Sponsored' in txt or 'Featured' in txt:
                        continue

                title_el = await item.query_selector('h3 a span')
                title = (await title_el.inner_text()).strip() if title_el else None
                link_el = await item.query_selector('h3 a')
                url = await link_el.get_attribute('href') if link_el else None
                if url and url.startswith('/'):
                    url = 'https://www.bestbuy.ca' + url

                # Price extraction
                price = None
                price_el = await item.query_selector('div.price__value') or await item.query_selector('div.price') or await item.query_selector('span[itemprop="price"]')
                if price_el:
                    price = parse_price(await price_el.inner_text())
                if not title or not price or price <= 0:
                    continue

                cpu = extract_cpu_from_title(title)
                ram_cap, ram_type = extract_ram_from_title(title)
                ssd = extract_ssd_from_title(title)
                screen = extract_screen_from_title(title)

                results.append({
                    'title': title,
                    'price': price,
                    'cpu_model': cpu,
                    'ram_capacity': ram_cap,
                    'ram_type': ram_type,
                    'ssd_capacity': ssd,
                    'screen_size': screen,
                    'url': url,
                    'source': 'BestBuy.ca'
                })
            except Exception:
                continue
        return results
    except Exception as e:
        print(f'BestBuy scrape error for "{search_term}": {e}')
        return []


async def scrape_canadacomputers(page, search_term, limit=10):
    url = f'https://www.canadacomputers.com/search/results_details.php?language=en&search={search_term.replace(" ", "+")}'
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_selector('div.product', timeout=15000)
        items = await page.query_selector_all('div.product')
        results = []
        for item in items:
            if len(results) >= limit:
                break
            try:
                title_el = await item.query_selector('a.productName') or await item.query_selector('a')
                title = (await title_el.inner_text()).strip() if title_el else None
                link_el = await item.query_selector('a.productName') or await item.query_selector('a')
                url = await link_el.get_attribute('href') if link_el else None
                if url and url.startswith('/'):
                    url = 'https://www.canadacomputers.com/' + url.lstrip('/')

                # Price extraction
                price = None
                price_el = await item.query_selector('span.price') or await item.query_selector('div.price') or await item.query_selector('span[itemprop="price"]')
                if price_el:
                    price = parse_price(await price_el.inner_text())
                if not title or not price or price <= 0:
                    continue

                cpu = extract_cpu_from_title(title)
                ram_cap, ram_type = extract_ram_from_title(title)
                ssd = extract_ssd_from_title(title)
                screen = extract_screen_from_title(title)

                results.append({
                    'title': title,
                    'price': price,
                    'cpu_model': cpu,
                    'ram_capacity': ram_cap,
                    'ram_type': ram_type,
                    'ssd_capacity': ssd,
                    'screen_size': screen,
                    'url': url,
                    'source': 'CanadaComputers'
                })
            except Exception:
                continue
        return results
    except Exception as e:
        print(f'CanadaComputers scrape error for "{search_term}": {e}')
        return []


# ----- Simple spec parsers -----

def extract_brand_from_title(title):
    brands = ['Dell', 'HP', 'Apple', 'Lenovo', 'Acer', 'Asus', 'Microsoft', 'Samsung', 'MSI', 'Razer', 'jumper', 'SGIN']
    for b in brands:
        if b.lower() in title.lower():
            return b
    return 'Generic'


def extract_cpu_from_title(title):
    # Look for common CPU patterns like i7-1185G7, M3 Pro, Ryzen 7 5800U, Celeron, Athlon
    m = re.search(r'([iI]\s?\d-[\w\d-]+|M\d\s?Pro|Ryzen\s?\d+\s?\w+|Celeron\s?\w+|Athlon\s?\w+)', title, re.I)
    if m:
        return m.group(0)
    # fallback: first token with digit
    m2 = re.search(r'([A-Za-z0-9\-]+\d{2,})', title)
    return m2.group(0) if m2 else None


def extract_ram_from_title(title):
    m = re.search(r'(\d+GB)\s*(DDR\d|Unified)?', title, re.I)
    if m:
        cap = m.group(1)
        typ = m.group(2) if m.group(2) else None
        return cap, typ
    return None, None


def extract_ssd_from_title(title):
    m = re.search(r'(\d+GB|\d+TB)\s*(SSD|nvme|SSD NVMe)?', title, re.I)
    if m:
        return m.group(1)
    return None


def extract_screen_from_title(title):
    m = re.search(r'(\d{1,2}(?:\.\d)?\")', title)
    return m.group(0) if m else None


# ----- CLI / Orchestrator -----

def main():
    parser = argparse.ArgumentParser(description='Laptop scrapers (demo or live)')
    parser.add_argument('--mode', choices=['demo', 'live'], default='demo', help='Run in demo or live mode')
    parser.add_argument('--limit', type=int, default=10, help='Max results per site per query')
    parser.add_argument('--no-save', action='store_true', help='Do not save results to the database (dry run)')
    parser.add_argument('--sites', nargs='+', choices=['amazon', 'bestbuy', 'canadacomputers'], default=['amazon','bestbuy','canadacomputers'], help='Sites to scrape')
    parser.add_argument('--proxies', nargs='*', help='List of proxy servers to use (e.g. http://ip:port)')
    parser.add_argument('--proxy-file', help='Path to file with proxies, one per line')
    parser.add_argument('--rotate-proxies', action='store_true', help='Rotate proxies per query')
    parser.add_argument('--randomize-ua', action='store_true', help='Randomize user agent per browser context')
    parser.add_argument('--stealth-level', choices=['basic','aggressive'], default='aggressive', help='Stealth profile level')
    parser.add_argument('--db-path', default=None, help='Override DB path (useful for tests/dry runs)')
    args = parser.parse_args()

    proxies = args.proxies or []
    if args.proxy_file:
        try:
            with open(args.proxy_file, 'r', encoding='utf-8') as f:
                proxies.extend([l.strip() for l in f if l.strip()])
        except Exception as e:
            print('Failed reading proxy file:', e)

    if args.mode == 'demo':
        demo_mode()
    else:
        # live mode
        if not HAS_PLAYWRIGHT:
            print("""Playwright not installed. To run live mode, install Playwright and browser binaries:
  pip install playwright
  playwright install chromium
Optionally: pip install playwright-stealth""")
            return
        try:
            asyncio.run(run_live_scrape(
                limit_per_site=args.limit,
                save=not args.no_save,
                sites=args.sites,
                proxies=proxies,
                rotate_proxies=args.rotate_proxies,
                randomize_ua=args.randomize_ua,
                stealth_level=args.stealth_level,
                db_path=args.db_path
            ))
        except Exception as e:
            print('Live scrape failed:', e)


if __name__ == '__main__':
    main()
