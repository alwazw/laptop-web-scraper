import asyncio
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper_laptops import scrape_amazon, _init_stealth
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='en-CA',
            timezone_id='America/Toronto'
        )
        await _init_stealth(context)
        page = await context.new_page()
        print('Running scrape_amazon...')
        res = await scrape_amazon(page, 'laptop', 10)
        print('\nFound', len(res), 'items')
        for r in res:
            print(f"Title: {r['title'][:50]}... Price: {r['price']}")

        await context.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
