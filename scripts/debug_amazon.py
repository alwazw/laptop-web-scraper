import asyncio
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper_laptops import scrape_amazon, _init_stealth
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        await _init_stealth(context)
        page = await context.new_page()
        await page.goto('https://www.amazon.ca/s?k=laptop')
        html = await page.content()
        print('\n-- page snapshot (first 2000 chars) --\n')
        print(html[:2000])

        # debug selectors
        s1 = await page.query_selector_all('div.s-result-item')
        s2 = await page.query_selector_all('div[data-component-type="s-search-result"]')
        print('\nSelector counts: s-result-item=', len(s1), 'data-component-type=', len(s2))

        # inspect first item
        if s1:
            first = s1[0]
            inner = await first.inner_html()
            print('\n-- first item HTML snippet (first 1200 chars) --')
            print(inner[:1200])
            sponsored_el = await first.query_selector('span.a-color-secondary')
            print('Sponsored element present:', bool(sponsored_el))
            offscreen = await first.query_selector('span.a-offscreen')
            whole = await first.query_selector('span.a-price-whole')
            frac = await first.query_selector('span.a-price-fraction')
            print('has a-offscreen:', bool(offscreen), 'has whole/fraction:', bool(whole), bool(frac))

        res = await scrape_amazon(page, 'laptop', 10)
        print('\nFound', len(res), 'items')
        for r in res[:5]:
            print(r)
        await context.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())