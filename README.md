# 💻 Laptop Arbitrage & Pricing Command Center

A sophisticated Python suite designed to identify undervalued laptops in the Canadian secondary market. By scraping real-time component prices (RAM/SSD) and laptop listings, the system calculates a "Base Chassis Cost" to reveal hidden arbitrage opportunities.

---

## 🚀 Key Features

- **Multi-Source Scraping**: Automated data ingestion from Amazon.ca, BestBuy.ca, CanadaComputers.com, and Newegg.ca.
- **Aggressive Anti-Detection**: Playwright-based scrapers with stealth profiles to bypass modern bot protections.
- **Spec-Based Deduplication**: Hardware-aware hashing (Brand + CPU + Screen) to compare identical models across different retailers.
- **Interactive Dashboard**: A modern Streamlit GUI for market trend visualization and real-time deal hunting.
- **Automated Scheduling**: Built-in background task runner for daily price updates.

---

## 🛠️ Installation

1. **Clone & Setup**:
   ```bash
   git clone https://github.com/alwazw/laptop-web-scraper.git
   cd laptop-arbitrage
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Initialize Database**:
   ```bash
   python db_setup.py
   ```

---

## 📈 Usage

### Launch the Dashboard
The easiest way to interact with the system:
```bash
streamlit run dashboard.py
```

### Manual Scraper Execution
- **Run Component Scraper** (Market baseline):
  ```bash
  python scraper_components.py
  ```
- **Run Laptop Scraper** (Live mode):
  ```bash
  python scraper_laptops.py --mode live --sites amazon bestbuy --limit 5
  ```
- **Run Full Pipeline**:
  ```bash
  python main.py
  ```

---

## 📂 Project Structure

- `dashboard.py`: Streamlit command center.
- `scraper_laptops.py`: Advanced laptop scraper with proxy/stealth support.
- `scraper_components.py`: RAM and SSD pricing baseline scraper.
- `data/arbitrage.db`: SQLite database storing all market intelligence.
- `main.py`: Orchestrates the full scraping and analysis pipeline.
- `documentation/`: Detailed technical specifications and strategies.

---

## 🤖 AI Agents
Agents working on this repository should refer to `AGENTS.md` for technical guidelines, verification steps, and project status.

---

## 📜 License
This project is licensed under the MIT License.
