# AGENTS.md - AI Agent Documentation 🤖

## Overview
This project is a **Laptop Arbitrage & Pricing Scraper** optimized for the Canadian market. It scrapes component prices (RAM, SSD) and laptop listings from major retailers (Amazon, BestBuy, Canada Computers, Newegg) to identify undervalued hardware.

## Current Project Status (Feb 2026)
- **Scraping**: Amazon.ca scraping is fully functional using "aggressive" stealth measures in Playwright.
- **Data Model**: Uses Spec-Hashing (Brand + CPU + Screen) for cross-retailer product identification.
- **GUI**: A Streamlit-based dashboard (`dashboard.py`) provides market visualization and deal hunting tools.
- **Database**: SQLite database at `data/arbitrage.db` with enforced foreign keys.

## Technical Stack
- **Language**: Python 3.12
- **Automation**: Playwright (with `playwright-stealth`)
- **Dashboard**: Streamlit, Plotly
- **Database**: SQLite3
- **Scheduling**: APScheduler

## Guidelines for Agents
1. **Stealth is Mandatory**: Always use the `aggressive` stealth profile in `scraper_laptops.py` and `scraper_components.py` for Amazon.ca.
2. **Pathing**: Use `pathlib` for all paths. The database must always be at `data/arbitrage.db`.
3. **Database Constraints**: `db_setup.py` enables `PRAGMA foreign_keys = ON`. Ensure all scripts use context managers for DB connections.
4. **Product Identification**: Never use retailer-specific IDs as primary keys for products. Always use the `product_hash` generated from hardware specs.

## Verification Commands
Before submitting changes, run these to ensure the project is stable:

- **Unit/E2E Tests**:
  ```bash
  pytest tests/
  ```
- **DB Setup**:
  ```bash
  python db_setup.py
  ```
- **Demo Scrape**:
  ```bash
  python scraper_laptops.py --mode demo
  ```
- **Dashboard Preview**:
  ```bash
  streamlit run dashboard.py --server.port 3000 --server.address 0.0.0.0 --server.enableCORS false
  ```

## Key Files
- `main.py`: Pipeline orchestrator.
- `scraper_laptops.py`: Core laptop scraping logic with proxy and stealth support.
- `scraper_components.py`: Scrapes RAM/SSD price baselines.
- `dashboard.py`: Streamlit frontend.
- `data_utils.py`: Centralized data access layer.
- `db_setup.py`: Schema definition and initialization.

## Documentation
Additional specs can be found in the `documentation/` folder:
- `technical_architecture.md`: Deep dive into the "Stripped Down" valuation logic.
- `product_strategy.md`: Refinements on RAM/SSD matching and arbitrage calculations.
- `database_schema.md`: SQL definitions.
