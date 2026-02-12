import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_utils import (
    fetch_component_history, fetch_latest_listings, get_latest_component_prices,
    get_db_stats, fetch_execution_logs, get_historical_baseline, calculate_tev,
    CONDITION_MARKDOWN
)
from scheduler_utils import start_scheduler, get_jobs
import subprocess
import sys
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Laptop Arbitrage Command Center v2.0",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4451; }
    .stDataFrame { border-radius: 10px; }
    .strategy-card { background-color: #262730; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; }
    .high-confidence { color: #00ff00; font-weight: bold; }
    .low-confidence { color: #ff9900; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🏢 Enterprise Control")
mode = st.sidebar.selectbox("Dashboard Mode", ["Market Pulse", "Deal Hunter", "Execution Audit", "Scraper Management"])

strategy = st.sidebar.radio("Active Strategy", ["Dropshipping (Spread)", "Inventory (Acquisition)"])

st.sidebar.divider()

def run_scraper(script_name, args=None):
    with st.spinner(f"Running {script_name}..."):
        cmd = [sys.executable, script_name]
        if args: cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr

if st.sidebar.button("🚀 Execute Full Pipeline"):
    run_scraper("main.py")

st.sidebar.divider()
st.sidebar.info("v2.0 Enterprise Solution | Stable 🟢")

# --- Main Content ---
st.title(f"🏢 Laptop Arbitrage: {strategy}")

stats = get_db_stats()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Market Listings", stats['total_listings'])
m2.metric("Spec Variants", stats['total_products'])
m3.metric("Component Baselines", stats['tracked_components'])
m4.metric("Last Data Freshness", datetime.now().strftime("%H:%M"))

if mode == "Market Pulse":
    st.header("📈 Market Valuation Framework")
    df_history = fetch_component_history()

    if not df_history.empty:
        col1, col2 = st.columns([3, 1])
        with col1:
            comp_types = st.multiselect("Filter Components", df_history['component_key'].unique(), default=df_history['component_key'].unique()[:5])
            df_filtered = df_history[df_history['component_key'].isin(comp_types)]
            fig = px.line(df_filtered, x='report_date', y='avg_price', color='component_key',
                         title="60-Day Component Volatility (CAD)", markers=True, template="plotly_dark")
            st.plotly_chart(fig, width='stretch')
        with col2:
            st.subheader("Liquidity Floor")
            latest_prices = get_latest_component_prices()
            for key, price in latest_prices.items():
                st.metric(label=key.replace('_', ' '), value=f"${price:.2f}")
    else:
        st.warning("Baseline data missing. Initialize scrapers.")

elif mode == "Deal Hunter":
    st.header("🎯 Dual-Valuation Decision Engine")

    df_listings = fetch_latest_listings()
    latest_components = get_latest_component_prices()

    if not df_listings.empty:
        # v2.0 Dual-Valuation Logic
        processed_data = []
        for _, row in df_listings.iterrows():
            hist_baseline = get_historical_baseline(row['product_hash'])
            tev = calculate_tev(row, latest_components, hist_baseline)

            margin = tev - row['listing_price']
            margin_pct = (margin / row['listing_price']) * 100 if row['listing_price'] > 0 else 0

            # Dropshipping spread logic
            spread = 0
            if strategy == "Dropshipping (Spread)":
                # Find max price for this product_hash in the market to calculate spread
                market_max = df_listings[df_listings['product_hash'] == row['product_hash']]['listing_price'].max()
                spread = (market_max - row['listing_price']) / row['listing_price'] * 100 if row['listing_price'] > 0 else 0

            processed_data.append({
                'Source': row['source'],
                'Condition': row['condition_tier'],
                'Title': row['listing_title'],
                'Price': row['listing_price'],
                'TEV (Est. Value)': round(tev, 2),
                'Margin $': round(margin, 2),
                'Margin %': round(margin_pct, 1),
                'Spread %': round(spread, 1),
                'Confidence': 'High' if hist_baseline else 'Low',
                'URL': row['url']
            })

        df_display = pd.DataFrame(processed_data)

        # Filtering
        col1, col2, col3 = st.columns(3)
        with col1:
            sources = st.multiselect("Retailers", df_display['Source'].unique(), default=df_display['Source'].unique())
        with col2:
            conditions = st.multiselect("Conditions", df_display['Condition'].unique(), default=df_display['Condition'].unique())
        with col3:
            min_margin = st.number_input("Min Margin %", value=5.0)

        df_filtered = df_display[
            (df_display['Source'].isin(sources)) &
            (df_display['Condition'].isin(conditions)) &
            (df_display['Margin %'] >= min_margin)
        ]

        if strategy == "Dropshipping (Spread)":
            df_filtered = df_filtered[df_filtered['Spread %'] >= 10.0]
            st.success(f"Identified {len(df_filtered)} arbitrage spreads > 10%")
        else:
            st.success(f"Identified {len(df_filtered)} undervalued inventory assets")

        st.dataframe(df_filtered.style.highlight_max(subset=['Margin %'], color='#004d00'), width='stretch')

    else:
        st.warning("No active listings. Run scrapers to populate.")

elif mode == "Execution Audit":
    st.header("📋 Execution Intelligence Audit")
    logs = fetch_execution_logs()
    if not logs.empty:
        st.table(logs)
    else:
        st.info("No execution history recorded.")

elif mode == "Scraper Management":
    st.header("⚙️ Scraper Orchestration")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Manual Adapters")
        if st.button("Run Component Scraper"): run_scraper("scraper_components.py")
        if st.button("Run Laptop Scraper (Live)"): run_scraper("scraper_laptops.py", ["--mode", "live"])

    with col2:
        st.subheader("Enterprise Scheduling")
        jobs = get_jobs()
        if jobs:
            for job in jobs: st.write(f"✅ **Task:** {job.id} | **Next run:** {job.next_run_time}")
        else:
            st.write("Scheduler: Inactive")
        if st.button("Enable Institutional Scheduling"):
            start_scheduler()
            st.rerun()

st.divider()
st.caption(f"Laptop Arbitrage v2.0-Enterprise | Build {datetime.now().strftime('%Y%m%d')}")
