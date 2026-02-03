# Laptop Arbitrage & Pricing Scraper

A robust Python application for discovering laptop arbitrage opportunities in Canadian markets by scraping price listings from major retailers and normalizing component costs.

---

## Objective 🎯
- Continuously collect laptop listings and component prices, compute "stripped chassis" costs and identify arbitrage opportunities where reselling yields net profit after fees and shipping.
- Prioritize correctness, anti-detection resilience, and maintainable, testable scraping code.

---

## Features
- Playwright-based scrapers with optional stealth support for anti-detection
- Component price scraping (Amazon, Newegg) with daily averages
- Laptop listing scraping (BestBuy, Amazon, CanadaComputers) with spec parsing, deduplication, and product identity hashing
- SQLite DB storing `components_tracking`, `component_daily_avg`, `products`, and `listings`
- Configurable CLI flags for demo/live runs, site selection, proxy rotation, stealth level, and dry-runs
- Tests and CI with guarded live smoke tests (disabled in CI by default)

---

## Project layout
- `db_setup.py` — create and migrate SQLite schema
- `scraper_components.py` — Playwright-based component scrapers (Amazon, Newegg)
- `scraper_laptops.py` — Laptop scrapers (demo & live modes), proxy rotation and stealth
- `analyzer.py` — analysis and report generation
- `main.py` — orchestrator pipeline
- `data/arbitrage.db` — SQLite database (moved to `data/`)
- `tests/` — unit and integration tests
- `scripts/` — helper utilities (`debug_amazon.py`, `agent_log.py`, etc.)
- `documentation/` — documentation and archived notes
- `AGENT.md` — agent handoff and triage directions
- `logs/agent_log.json` — actionable agent log (record actions and unresolved items)

---

## Installation
1. Clone the repo
2. Create and activate venv
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
   ```
3. Install Python dependencies
   ```bash
   pip install -r requirements.txt
   # or at minimum:
   pip install playwright pytest
   pip install playwright-stealth  # optional, recommended
   playwright install chromium
   ```

---

## Usage examples
- Initialize DB:
  ```bash
  python db_setup.py
  ```
- Demo laptop scrape (safe):
  ```bash
  python scraper_laptops.py --mode demo
  ```
- Live scrape (dry run, Amazon only):
  ```bash
  python scraper_laptops.py --mode live --sites amazon --limit 5 --no-save --randomize-ua
  ```
- Run full pipeline:
  ```bash
  python main.py
  ```

---

## Agents & Handoff
- See `AGENT.md` for detailed handoff steps, the current unresolved issues, and instructions for reproducing the Amazon parsing problem.
- Use `.scripts/agent_log.py` to add entries, append/resolve unresolved issues, and mark features done.

---

## Troubleshooting & Triage Notes
- Amazon scraping can be blocked or return pages where prices are lazy-loaded or hidden. Use headful `headless=False`, Playwright tracing, screenshots, and network HAR capture to inspect.
- If scraping is blocked by IP or fingerprinting, enable proxy rotation and `playwright-stealth`.

---

## CI / Tests
- Run tests locally: `python -m pytest -q` (CI uses `RUN_LIVE_SMOKE=0` to avoid live runs)
- CI workflow at `.github/workflows/ci.yml` installs Playwright browsers and runs tests.

---

## Contributing & Docs
- Update `Docs/` and `AGENT.md` when implementing features and resolving issues.
- Use `python .scripts/agent_log.py feature-done "<desc>" --notes "update docs"` to mark feature completion and remind to edit docs.

---

## Recommended next steps (for you or next agent)
1. Reproduce Amazon price extraction problem in `debug_amazon.py` with `--stealth-level aggressive`, screenshots, and tracing.
2. Harden selectors and add wait-for-XHR where prices are loaded asynchronously.
3. Consider small SQLite-backed agent log if you need strong querying or concurrency.

---

## License
MIT

---

If you'd like, I can generate a `requirements.txt`, add examples, or create a quick dev container to make onboarding smoother. Want me to proceed with any of these? (I can also push these changes to the remote `main` branch if you confirm.)