# Agent Handoff & Next Steps 🚀

## Purpose
Provide clear context, tests, and an actionable to-do list for the next agent to continue development and triage live scraping issues.

---

## Quick summary (2 sentences)
- This repo contains a laptop arbitrage scraper. The components scraper (Playwright) successfully pulls RAM/SSD prices; the laptop scraper has been upgraded to support live parsing with Playwright (stealth, proxies, rotation) but currently returns 0 parsed listings on Amazon during live runs. 
- Primary unresolved issue: Amazon search pages load but expected price markup is often absent from inspected result nodes (likely due to dynamic rendering, widgets, or anti-bot behavior). See “Unresolved issues” below.

---

## Environment & How to run (💡 essential)
- Python venv (3.12). Activate with your venv activation script.
- Install dependencies:
  - pip install -r requirements.txt (or: pip install playwright pytest playwright-stealth)
  - playwright install chromium
- Run tests: `python -m pytest -q` (CI uses RUN_LIVE_SMOKE=0 by default)
- Demo run (safe): `python scraper_laptops.py --mode demo`
- Live dry-run (no-save): `python scraper_laptops.py --mode live --sites amazon --limit 3 --no-save --randomize-ua`
- Debug Amazon manually: `python ./scripts/debug_amazon.py`

---

## Files of interest (changes & responsibilities)
- `scraper_laptops.py` 🔧 — main laptop scraping logic
  - Modes: `--mode demo | live`
  - Options: `--sites`, `--proxies`, `--proxy-file`, `--rotate-proxies`, `--randomize-ua`, `--stealth-level`, `--db-path`
  - Proxy rotation implemented via `ProxyManager`
  - Stealth: uses `playwright_stealth` if present, fallback scripts otherwise
- `scraper_components.py` ✅ — working Playwright component scrapers (Amazon / Newegg)
- `tests/` ✅ — unit tests (`test_parsers.py`) and e2e smoke tests (`test_e2e.py`), and `tests/test_proxy_manager.py`
- `.github/workflows/ci.yml` ✅ — CI that runs tests (live smoke disabled by default)
- `scripts/debug_amazon.py` 🔍 — helper to dump Amazon page HTML and run `scrape_amazon` for inspection

---

## Unresolved issues (actionable list)
1. **Amazon parsing returns 0 items** (highest priority)
   - Observed: Search page loads; `div[data-component-type="s-search-result"]` exists, but first product nodes often lack `span.a-offscreen` / price markers. `debug_amazon.py` printed an HTML snapshot showing widget-like nodes as the first items. This indicates either:
     - content is lazy-loaded after additional JS execution, or
     - Amazon is serving a bot-protected variant (missing prices), or
     - our selectors need broader fallback coverage.
   - Recommended triage steps (in order):
     1. Run live debug with `--stealth-level aggressive --randomize-ua --no-save` and inspect page HTML and console logs.
     2. Try headful mode (set headless=False in runLive) to visually inspect page. Use Playwright tracing / screenshot to confirm price rendering.
     3. Increase waits and check for lazy-loaded price containers (observe network XHRs for price payloads). Use `page.wait_for_response()` on likely XHR endpoints.
     4. Capture HAR or network logs and examine for price JSON payloads.
     5. If persistent blocking: route traffic through a trusted proxy or scraping API to isolate IP-based blocking.
2. **Selector hardening for BestBuy/CanadaComputers**
   - Not failing now, but add more fallbacks and unit tests once Amazon parsing is stable.

---

## Short-term roadmap for the next agent (prioritized)
1. Reproduce the Amazon issue locally with tracing and screenshots. (Essential) ✅
2. Implement the triage steps above; iterate selectors and add robust waits and detection for widgets vs product nodes. 🔁
3. Add more logs to `logs/agent_log.json` via `scripts/agent_log.py` (see below) for every attempted live scrape and any errors encountered. 🧾
4. If Amazon cannot be reliably scraped, evaluate alternatives: scraping API (e.g., ScrapingBee), or retailer APIs if available. ⚖️

---

## How to report progress
- Use `scripts/agent_log.py` to record each attempt and error, which updates `logs/agent_log.json`. This file is intended to be machine-readable and human-friendly (see `scripts/README` section below).

---

## Contact / context
- Tests and CI are configured; do not enable live smoke tests in CI by default. Use env `RUN_LIVE_SMOKE=1` to run them locally or in a controlled CI run.

---

Good luck — the most effective next step is **reproducing the Amazon no-price behavior with tracing/screenshot** so we can see whether it's dynamic content or anti-bot behavior. 🧭

---

# Origin / Claim
This file combines the earlier `Agent0-1.md` completion summary with the handoff-oriented `AGENT.md`. The original `Agent0-1.md` is archived in `Docs/Agent0-1.original.md` for historical reference. The merged content reflects current reality — some features were implemented, and some issues (e.g., Amazon parsing) are unresolved and documented above.

# Progress tracking conventions (for agents)
- Use `.scripts/agent_log.py` to record every attempt and error, with `add`, `append-unresolved`, `set-unresolved`, `resolve`, `feature-done`, `clear-unresolved`, and `show` commands.
- When resolving an unresolved issue, use `python .scripts/agent_log.py resolve "<issue text>" --notes "<summary>"` to remove it from `unresolved` and add a `done` entry in the log. This keeps `agent_log.json` clean and actionable.
- When a feature is completed, use `python .scripts/agent_log.py feature-done "<feature description>" --notes "<what changed>"` which will add a `done` log and remind the agent to update `README.md` and `Docs/` as needed.
- We intentionally use `agent_log.json` (simple JSON) for portability. For production and richer queryability, a small SQLite-backed store would be preferable; this repo keeps JSON for simplicity but includes a plan to add a migration script if needed in the future.
- After marking a feature done, update the `Docs/` directory and `README.md` to reflect the implemented feature. Add a `docs` entry in the log using `feature-done` so reviewers can see where docs were expected to be updated.

