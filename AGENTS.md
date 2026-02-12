# AGENTS.md - AI Agent Documentation 🤖 (v2.0 Enterprise)

## Overview
This project is an **Enterprise Laptop Arbitrage & Pricing Intelligence System** (v2.0). It uses a dual-valuation framework to identify high-margin opportunities in the Canadian secondary market.

## v2.0 Enterprise Features
- **Dual-Valuation Engine**: TEV = MAX(Component Harvest, Condition-Adjusted Chassis).
- **7 Retailers**: Amazon, BestBuy, Walmart, CanadaComputers, Staples, Dell, HP.
- **Strategy Selection**: Toggle between Dropshipping (Spread) and Inventory (Acquisition).
- **Historical Baselines**: 60-day price tracking for high-confidence valuations.
- **Audit Logs**: Full transparency into execution health and arbitrage decisions.

## Technical Stack
- **Language**: Python 3.12
- **Scraping**: Playwright Stealth (Aggressive Profile)
- **Analytics**: Dual-Logic Valuation Framework
- **Frontend**: Streamlit v2.0 Command Center
- **Database**: SQLite3 with Foreign Key Enforcement

## Strategic Guidelines
1. **Deduplication**: Always use Spec-Hashing (Brand + CPU + Screen) to unify listings.
2. **Confidence Scoring**: Flag deals with < 3 historical data points as "Low Confidence".
3. **Markdown Matrix**:
   - New (1.0), OpenBox (0.9), Refurbished Excellent (0.85), Good (0.75), Fair (0.6), Other (0.5).
4. **Data Freshness**: Maintain a 2-hour refresh window for live arbitrage.

## Verification Commands
- **Run Pipeline**: `python main.py`
- **Dashboard**: `streamlit run dashboard.py`
- **Tests**: `pytest tests/`

## Key Files
- `analyzer.py`: v2.0 Decision Engine.
- `data_utils.py`: Valuation logic and DB access.
- `scraper_laptops.py`: Multi-retailer scraper adapters.
- `db_setup.py`: v2.0 Relational schema.
