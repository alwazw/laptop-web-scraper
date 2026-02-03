# Agent Zero Prompt

# Role: Senior Python Automation Engineer

# Mission: Build a "Laptop Arbitrage & Pricing Scraper"

You are tasked with building a robust Python application that scrapes laptop prices, calculates component costs, and generates daily deal reports.

## Core Requirements

1. **Anti-Detection:** You MUST use `playwright` with `playwright-stealth` (or equivalent headers) to bypass anti-bot protection on Amazon, BestBuy, and Dell.
2. **Database:** Use SQLite (`data/arbitrage.db`) to store all data.
3. **Idempotency:** The script must be able to run daily without crashing on duplicate data (use correct UPSERT or checking logic).

## Phase 1: Database Setup

Initialize the database using this exact schema. Do not deviate.

```
CREATE TABLE IF NOT EXISTS components_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, -- 'RAM' or 'SSD'
    subtype TEXT, -- 'DDR4', 'DDR5', 'NVMe'
    capacity TEXT NOT NULL, -- '8GB', '1TB'
    price REAL NOT NULL,
    url TEXT,
    source TEXT,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS component_daily_avg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE NOT NULL,
    component_key TEXT NOT NULL, -- e.g. 'RAM_DDR4_8GB'
    avg_price REAL NOT NULL,
    UNIQUE(report_date, component_key)
);

CREATE TABLE IF NOT EXISTS products (
    product_hash TEXT PRIMARY KEY, -- Hash of Brand+CPU+Screen
    brand TEXT,
    guessed_model TEXT,
    cpu_model TEXT,
    screen_size TEXT,
    is_ram_upgradeable INTEGER DEFAULT 1, -- 1 for Yes, 0 for No
    is_ssd_upgradeable INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_hash TEXT,
    source TEXT, -- 'BestBuy', 'Amazon', 'CanadaComputers'
    condition TEXT, -- 'New', 'OpenBox', 'Refurb'
    listing_title TEXT,
    listing_price REAL NOT NULL,
    cpu_spec TEXT,
    ram_spec_capacity TEXT, -- '16GB'
    ram_spec_type TEXT, -- 'DDR4' or 'DDR5'
    ssd_spec_capacity TEXT, -- '512GB'
    url TEXT,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_hash) REFERENCES products(product_hash)
);

```

## Phase 2: The Component Scraper (Runs First)

**Objective:** Establish the baseline "value" of RAM and SSDs for the day.

1. **Sources:** Scrape **Amazon.ca** and **Newegg.ca**.
2. **Targets:**
    - **RAM:** 8GB, 16GB, 32GB (Search for both DDR4 and DDR5 variants).
    - **SSD:** 256GB, 512GB, 1TB, 2TB (NVMe M.2 only).
3. **Logic:**
    - Search for the term (e.g., "16GB DDR5 Laptop RAM").
    - Sort by lowest price.
    - **Ignore** "Sponsored" or "Promoted" listings.
    - Capture the **lowest 3** valid prices.
    - Save individual records to `components_tracking`.
    - Calculate the average of those 3 and save to `component_daily_avg` with today's date.

## Phase 3: The Laptop Scraper (Runs Second)

**Objective:** Collect laptop listings to find deals.

1. **Sources:** BestBuy.ca (Open Box/Marketplace), Amazon.ca (Renewed), Dell.ca (Outlet/Refurb), CanadaComputers (Open Box).
2. **Normalization Strategy (Crucial):**
    - You must generate a `product_hash` for every laptop found.
    - **Hash Formula:** `SHA256(Brand + CPU_Model + Screen_Resolution + Screen_Size)`.
    - *Example:* "Dell_i7-1185G7_1920x1080_14".
    - If this hash does not exist in the `products` table, create it.
3. **Upgradeability Heuristic:**
    - When creating the `product` entry:
    - IF description contains "LPDDR", "Soldered", "Onboard", or "Unified" (Mac) -> Set `is_ram_upgradeable = 0`.
    - ELSE -> Set `is_ram_upgradeable = 1`.
4. **CPU Parsing Logic:**
    - You must extract the CPU model to determine RAM generation.
    - *Intel 8th-11th Gen* -> defaults to DDR4 prices.
    - *Intel 12th+ Gen / Ultra* -> defaults to DDR5 prices.

## Phase 4: Analysis & Reporting

**Objective:** Generate the "Stripped Down" cost analysis.

For every laptop listing found today:

1. **Fetch Baseline Costs:** Get today's `avg_price` from `component_daily_avg` for the RAM and SSD specified in the laptop listing.
2. **Calculate Deduction:**
    - `RAM_Value` = (Avg Price of that RAM) * (is_ram_upgradeable).
    - `SSD_Value` = (Avg Price of that SSD) * (is_ssd_upgradeable).
    - *Note: If not upgradeable, value is 0 because we can't strip it.*
3. **Stripped Down Price:** `Listing_Price - RAM_Value - SSD_Value`.

## Phase 5: The Output Reports

Generate a Markdown file or print to console:

**Report 1: Tiered Best Deals (Based on Listing Price)**

- **Tier 1:** <$600 (Top 5 sorted by value)
- **Tier 2:** <$700 (Top 5)
- **Tier 3:** <$800 (Top 5)

**Report 2: Sourcing Opportunities (Based on Stripped Price)**

- List laptops with the lowest *Stripped Down Price*. These are candidates to buy, upgrade, and resell.

**Report 3: Drop-shipping/Arbitrage Candidates**

- Find listings sharing the same `product_hash`.
- Compare prices between Source A (e.g., BestBuy) and Source B (e.g., Amazon).
- **Formula:** IF `(Price_Source_B - Price_Source_A) > (Price_Source_A * 0.15 + 20)`
- *Explanation:* The gap must cover 15% marketplace fees + $20 estimated shipping.
- List these matches.

## Execution Plan

1. Write `db_setup.py` to init the DB.
2. Write `scraper_components.py` to get RAM/SSD avgs.
3. Write `scraper_laptops.py` to get laptop listings.
4. Write `analyzer.py` to query DB and generate reports.
5. Create a `main.py` orchestrator to run them in order.

Start by coding the Database Setup and the Component Scraper.