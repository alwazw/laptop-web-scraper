import asyncio
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import hashlib

# Configuration
DB_PATH = str(Path(__file__).resolve().parents[1] / 'data' / 'arbitrage.db')

async def scrape_amazon_ca(page, search_term):
    """Scrape Amazon.ca for lowest 3 valid prices"""
    try:
        await page.goto(f'https://www.amazon.ca/s?k={search_term.replace(" ", "+")}', timeout=30000)
        
        # Wait for search results
        await page.wait_for_selector('div.s-result-item', timeout=30000)
        
        # Get all result items
        items = await page.query_selector_all('div.s-result-item')
        
        prices = []
        
        for item in items[:20]:  # Check first 20 items
            try:
                # Skip sponsored items
                sponsored = await item.query_selector('span.a-color-secondary')
                if sponsored:
                    text = await sponsored.inner_text()
                    if 'Sponsored' in text or 'Promoted' in text:
                        continue
                
                # Get price
                price_elem = await item.query_selector('span.a-price-whole')
                if price_elem:
                    price_text = await price_elem.inner_text()
                    price_match = re.search(r'(\d+,)?\d+', price_text)
                    if price_match:
                        price_str = price_match.group(0).replace(',', '')
                        if price_str.isdigit():
                            price = float(price_str)
                            if price > 0:
                                prices.append(price)
            except Exception as e:
                continue
        
        return sorted(prices)[:3]
    except Exception as e:
        print(f'Error scraping Amazon.ca for {search_term}: {e}')
        return []

async def scrape_newegg_ca(page, search_term):
    """Scrape Newegg.ca for lowest 3 valid prices"""
    try:
        await page.goto(f'https://www.newegg.ca/p/pl?d={search_term.replace(" ", "+")}', timeout=30000)
        
        # Wait for search results
        await page.wait_for_selector('div.item-cell', timeout=30000)
        
        # Get all result items
        items = await page.query_selector_all('div.item-cell')
        
        prices = []
        
        for item in items[:20]:  # Check first 20 items
            try:
                # Skip sponsored items
                sponsored = await item.query_selector('div.ad-badge')
                if sponsored:
                    continue
                
                # Get price
                price_elem = await item.query_selector('li.price-current strong')
                if price_elem:
                    price_text = await price_elem.inner_text()
                    price_match = re.search(r'(\d+,)?\d+\.\d+', price_text)
                    if price_match:
                        price_str = price_match.group(0).replace(',', '')
                        try:
                            price = float(price_str)
                            if price > 0:
                                prices.append(price)
                        except ValueError:
                            pass
            except Exception as e:
                continue
        
        return sorted(prices)[:3]
    except Exception as e:
        print(f'Error scraping Newegg.ca for {search_term}: {e}')
        return []

async def save_component_data(component_type, subtype, capacity, price, url, source):
    """Save individual component data to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO components_tracking (type, subtype, capacity, price, url, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (component_type, subtype, capacity, price, url, source))
        conn.commit()
    except Exception as e:
        print(f'Error saving component data: {e}')
    finally:
        conn.close()

async def save_daily_avg(component_key, avg_price):
    """Save daily average to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT OR REPLACE INTO component_daily_avg (report_date, component_key, avg_price)
            VALUES (?, ?, ?)
        ''', (today, component_key, avg_price))
        conn.commit()
    except Exception as e:
        print(f'Error saving daily avg: {e}')
    finally:
        conn.close()

async def scrape_components():
    """Main component scraping function"""
    print('Starting component scraping...')
    
    # Component targets
    ram_targets = [
        ('RAM', 'DDR4', '8GB'),
        ('RAM', 'DDR4', '16GB'),
        ('RAM', 'DDR4', '32GB'),
        ('RAM', 'DDR5', '8GB'),
        ('RAM', 'DDR5', '16GB'),
        ('RAM', 'DDR5', '32GB')
    ]
    
    ssd_targets = [
        ('SSD', 'NVMe', '256GB'),
        ('SSD', 'NVMe', '512GB'),
        ('SSD', 'NVMe', '1TB'),
        ('SSD', 'NVMe', '2TB')
    ]
    
    all_targets = ram_targets + ssd_targets
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Apply basic stealth by setting headers and properties
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            """
        )
        
        # Create page
        page = await context.new_page()
        
        # Scrape each target
        for component_type, subtype, capacity in all_targets:
            print(f'Scraping {component_type} {subtype} {capacity}...')
            
            # Search terms
            if component_type == 'RAM':
                search_terms = [f'{capacity} {subtype} Laptop RAM', f'{capacity} {subtype} RAM for laptop']
            else:  # SSD
                search_terms = [f'{capacity} NVMe M.2 SSD', f'{capacity} NVMe SSD laptop']
            
            all_prices = []
            
            # Try Amazon.ca
            for search_term in search_terms:
                prices = await scrape_amazon_ca(page, search_term)
                all_prices.extend(prices)
                if len(all_prices) >= 3:
                    break
            
            # Try Newegg.ca if we don't have enough prices
            if len(all_prices) < 3:
                for search_term in search_terms:
                    prices = await scrape_newegg_ca(page, search_term)
                    all_prices.extend(prices)
                    if len(all_prices) >= 3:
                        break
            
            # Take top 3 lowest prices
            if all_prices:
                top_3_prices = sorted(all_prices)[:3]
                avg_price = sum(top_3_prices) / len(top_3_prices)
                
                # Save individual prices
                for price in top_3_prices:
                    await save_component_data(component_type, subtype, capacity, price, 
                                            f'https://www.amazon.ca/search?q={search_term.replace(" ", "+")}', 
                                            'Amazon.ca')
                
                # Save daily average
                component_key = f'{component_type}_{subtype}_{capacity}'
                await save_daily_avg(component_key, avg_price)
                
                print(f'  {component_type} {subtype} {capacity}: {top_3_prices} -> Avg: ${avg_price:.2f}')
            else:
                print(f'  No prices found for {component_type} {subtype} {capacity}')
        
        await browser.close()
    
    print('Component scraping completed.')

if __name__ == '__main__':
    asyncio.run(scrape_components())