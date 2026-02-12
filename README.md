# 🏢 Laptop Arbitrage Enterprise Command Center (v2.0)

Institutional-grade arbitrage intelligence for the Canadian secondary electronics market.

---

## 🎯 Dual-Valuation Framework

v2.0 implements a **Max-Value Principle**, calculating the **Total Estimated Value (TEV)** of every laptop based on two independent vectors:
1. **Component Harvest**: The liquid value of modular parts (RAM/SSD) based on real-time market averages.
2. **Condition-Adjusted Chassis**: Statistical valuation against historical "New" baselines, adjusted for condition (OpenBox, Refurbished, etc.).

---

## 🚀 Enterprise Features

- **7-Node Market Triangulation**: Real-time data from Amazon, BestBuy, Walmart, CanadaComputers, Staples, Dell, and HP.
- **Arbitrage Strategies**:
    - **Dropshipping**: Exploiting cross-retailer price spreads (>10%).
    - **Inventory Acquisition**: High-yield sourcing for resale or harvesting.
- **Intelligence Dashboard**: Modern Streamlit GUI with confidence scoring, historical volatility charts, and automated scheduling.
- **Audit Resilience**: Comprehensive logging of scraper execution and financial decision-making logic.

---

## 🛠️ Quick Start

1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Initialize Engine**:
   ```bash
   python db_setup.py
   ```

3. **Launch Command Center**:
   ```bash
   streamlit run dashboard.py
   ```

---

## 📂 Architecture

- **`scraper_laptops.py`**: Multi-retailer adapters with stealth anti-detection.
- **`data_utils.py`**: Dual-valuation implementation and data persistence.
- **`analyzer.py`**: Automated decision engine and margin analysis.
- **`db_setup.py`**: Relational SQLite schema with foreign key integrity.

---

## 🤖 AI Agents
Refer to `AGENTS.md` for technical mandates and verification protocols.

---

## 📜 License
MIT License | Built for institutional laptop arbitrage.
