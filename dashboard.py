import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_utils import (
    fetch_component_history, fetch_latest_listings, get_latest_component_prices,
    get_db_stats, fetch_execution_logs, get_historical_baseline, calculate_tev,
    CONDITION_MARKDOWN, load_scraper_config, save_scraper_config
)
from scheduler_utils import start_scheduler, get_jobs
import subprocess
import sys
import os
from datetime import datetime

# --- Page Config ---
st.set_page_config(
    page_title="Arbitrage Command Center v2.1",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Initialization ---
if 'active_view' not in st.session_state:
    st.session_state.active_view = "Overview"
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None

# --- Custom Styling ---
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #1e2130;
        padding: 1.5rem;
        border-radius: 0.8rem;
        border: 1px solid #3e4451;
        transition: transform 0.2s;
    }
    .stMetric:hover {
        transform: translateY(-5px);
        border-color: #6a0dad;
    }
    .opportunity-card {
        background: linear-gradient(135deg, #1e2130 0%, #2c3143 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        border-left: 5px solid #6a0dad;
        margin-bottom: 1rem;
    }
    .metric-button {
        width: 100%;
        border: none;
        background: transparent;
        text-align: left;
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("🏢 Enterprise Arbitrage")
    st.divider()

    nav_options = {
        "Overview": "🏠 Overview",
        "Deal Hunter": "🎯 Real-Time Arbitrage",
        "Market Trends": "📈 Market Intelligence",
        "Execution Audit": "📋 System Logs",
        "Settings": "⚙️ Scraper Config"
    }

    st.session_state.active_view = st.radio(
        "Navigation",
        options=list(nav_options.keys()),
        format_func=lambda x: nav_options[x],
        label_visibility="collapsed"
    )

    st.divider()
    st.subheader("Global Strategy Filters")
    enable_dropship = st.checkbox("Dropshipping Deals", value=True)
    enable_inventory = st.checkbox("Inventory Sourcing", value=True)

    st.divider()
    st.info("System Status: Operational 🟢")
    if st.button("🚀 Force Run Pipeline"):
        with st.spinner("Executing Full Pipeline..."):
            subprocess.run([sys.executable, "main.py"])
            st.rerun()

# --- Shared Data Fetching ---
stats = get_db_stats()
latest_listings = fetch_latest_listings()
latest_components = get_latest_component_prices()

# --- View Logic ---

if st.session_state.active_view == "Overview":
    st.title("🏠 Market Overview")

    # Row 1: Clickable Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Listings", stats['total_listings'])
        if st.button("Explore Raw Data", key="btn_listings"):
            st.session_state.active_view = "Deal Hunter"
            st.rerun()
    with c2:
        st.metric("Spec Variants", stats['total_products'])
        if st.button("View Inventory", key="btn_products"):
            st.session_state.active_view = "Market Trends"
            st.rerun()
    with c3:
        st.metric("Price Baselines", stats['tracked_components'])
        if st.button("Analyze Volatility", key="btn_components"):
            st.session_state.active_view = "Market Trends"
            st.rerun()
    with c4:
        st.metric("Last Sync", stats['last_update'])
        if st.button("Check Health", key="btn_health"):
            st.session_state.active_view = "Execution Audit"
            st.rerun()

    st.divider()

    # Row 2: Immediate Opportunities
    col1, col2 = st.columns(2)

    # Process Opportunities
    dropship_deals = []
    inventory_deals = []

    if not latest_listings.empty:
        for _, row in latest_listings.iterrows():
            hist_baseline = get_historical_baseline(row['product_hash'])
            tev, harvest, chassis = calculate_tev(row, latest_components, hist_baseline)

            margin = tev - row['listing_price']
            margin_pct = (margin / row['listing_price']) * 100 if row['listing_price'] > 0 else 0

            # Dropship spread
            market_max = latest_listings[latest_listings['product_hash'] == row['product_hash']]['listing_price'].max()
            spread = (market_max - row['listing_price']) / row['listing_price'] * 100 if row['listing_price'] > 0 else 0

            deal_obj = {
                'title': row['listing_title'],
                'price': row['listing_price'],
                'margin_pct': margin_pct,
                'spread': spread,
                'source': row['source'],
                'confidence': 'High' if hist_baseline else 'Low',
                'url': row['url']
            }

            if spread >= 10.0: dropship_deals.append(deal_obj)
            if margin_pct >= 10.0: inventory_deals.append(deal_obj)

    with col1:
        st.subheader("📦 Top Dropshipping Opportunities")
        if dropship_deals:
            top_ds = sorted(dropship_deals, key=lambda x: x['spread'], reverse=True)[:3]
            for deal in top_ds:
                with st.container():
                    st.markdown(f"""
                    <div class="opportunity-card">
                        <h4>{deal['title'][:60]}...</h4>
                        <p>Spread: <b>{deal['spread']:.1f}%</b> | Price: ${deal['price']}</p>
                        <p>Source: {deal['source']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("Buy Link", deal['url'])
        else:
            st.info("No high-spread dropshipping opportunities found.")

    with col2:
        st.subheader("🏢 Top Inventory Acquisitions")
        if inventory_deals:
            top_inv = sorted(inventory_deals, key=lambda x: x['margin_pct'], reverse=True)[:3]
            for deal in top_inv:
                with st.container():
                    st.markdown(f"""
                    <div class="opportunity-card" style="border-left-color: #00ff00;">
                        <h4>{deal['title'][:60]}...</h4>
                        <p>Margin: <b>{deal['margin_pct']:.1f}%</b> | Confidence: {deal['confidence']}</p>
                        <p>Source: {deal['source']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("Source Unit", deal['url'])
        else:
            st.info("No undervalued inventory found.")

elif st.session_state.active_view == "Deal Hunter":
    st.title("🎯 Real-Time Arbitrage Engine")

    if latest_listings.empty:
        st.warning("No listings found. Run scraper.")
    else:
        # Strategy filtering
        processed = []
        for _, row in latest_listings.iterrows():
            hist_baseline = get_historical_baseline(row['product_hash'])
            tev, harvest, chassis = calculate_tev(row, latest_components, hist_baseline)

            margin = tev - row['listing_price']
            margin_pct = (margin / row['listing_price']) * 100 if row['listing_price'] > 0 else 0

            market_max = latest_listings[latest_listings['product_hash'] == row['product_hash']]['listing_price'].max()
            spread = (market_max - row['listing_price']) / row['listing_price'] * 100 if row['listing_price'] > 0 else 0

            show = False
            if enable_dropship and spread >= 10.0: show = True
            if enable_inventory and margin_pct >= 5.0: show = True

            if show:
                processed.append({
                    'id': row['id'],
                    'Retailer': row['source'],
                    'Title': row['listing_title'],
                    'Price': row['listing_price'],
                    'TEV': round(tev, 2),
                    'Margin %': round(margin_pct, 1),
                    'Spread %': round(spread, 1),
                    'Method': 'Chassis' if hist_baseline else 'Harvest',
                    'row': row,
                    'harvest': harvest,
                    'chassis': chassis
                })

        df_p = pd.DataFrame(processed)
        if not df_p.empty:
            st.dataframe(
                df_p[['Retailer', 'Title', 'Price', 'TEV', 'Margin %', 'Spread %', 'Method']],
                width='stretch',
                selection_mode="single_row",
                on_select="rerun",
                key="deal_table"
            )

            # Drill down view
            selected_rows = st.session_state.deal_table.get("selection", {}).get("rows", [])
            if selected_rows:
                idx = selected_rows[0]
                deal = processed[idx]
                st.divider()
                st.header("🔍 Opportunity Analysis")
                ac1, ac2 = st.columns(2)
                with ac1:
                    st.subheader("Valuation Breakdown")
                    st.write(f"**Calculated TEV:** ${deal['TEV']}")
                    st.write(f"**Component Harvest Value:** ${deal['harvest']:.2f}")
                    st.write(f"**Condition-Adjusted Chassis:** ${deal['chassis']:.2f}")
                    st.info(f"Why relevant: This unit is priced at **${deal['Price']}**, which is **{deal['Margin %']}%** below its intrinsic value of ${deal['TEV']}.")
                with ac2:
                    st.subheader("Hardware Profile")
                    st.json(deal['row'].to_dict())
                    st.link_button("Open Listing", deal['row']['url'])
        else:
            st.info("No deals match current filters.")

elif st.session_state.active_view == "Market Trends":
    st.title("📈 Market Intelligence")
    df_history = fetch_component_history()
    if not df_history.empty:
        comp_types = st.multiselect("Select Components", df_history['component_key'].unique(), default=df_history['component_key'].unique()[:5])
        df_f = df_history[df_history['component_key'].isin(comp_types)]
        fig = px.line(df_f, x='report_date', y='avg_price', color='component_key', title="Component Price Evolution")
        st.plotly_chart(fig, width='stretch')

    st.divider()
    st.subheader("Current Market Liquidity (Components)")
    l_prices = get_latest_component_prices()
    st.json(l_prices)

elif st.session_state.active_view == "Execution Audit":
    st.title("📋 Execution Intelligence Audit")
    logs = fetch_execution_logs()

    col1, col2 = st.columns([1, 3])
    with col1:
        status_filter = st.multiselect("Filter Status", ["success", "failure"], default=["success", "failure"])
        scraper_filter = st.multiselect("Filter Scraper", logs['scraper_name'].unique(), default=logs['scraper_name'].unique())

    df_logs = logs[(logs['status'].isin(status_filter)) & (logs['scraper_name'].isin(scraper_filter))]

    st.dataframe(df_logs, width='stretch')

elif st.session_state.active_view == "Settings":
    st.title("⚙️ Scraper Configuration")

    config = load_scraper_config() or {
        "queries": ["laptop"],
        "sites": ["amazon", "bestbuy", "canadacomputers", "walmart", "staples", "dell", "hp"],
        "limit": 10,
        "schedule_time": "02:00"
    }

    with st.form("config_form"):
        queries = st.text_area("Search Queries (comma separated)", value=", ".join(config['queries']))
        sites = st.multiselect("Target Sites", ["amazon", "bestbuy", "canadacomputers", "walmart", "staples", "dell", "hp"], default=config['sites'])
        limit = st.number_input("Limit per site", value=config['limit'])
        sched = st.time_input("Recurring Daily Run", value=datetime.strptime(config['schedule_time'], "%H:%M").time())

        if st.form_submit_button("💾 Save & Apply Config"):
            new_config = {
                "queries": [q.strip() for q in queries.split(",")],
                "sites": sites,
                "limit": limit,
                "schedule_time": sched.strftime("%H:%M")
            }
            save_scraper_config(new_config)
            st.success("Configuration updated!")

    st.divider()
    st.subheader("Automation Control")
    jobs = get_jobs()
    if jobs:
        for job in jobs: st.write(f"✅ **Task Active:** {job.id} | Next Run: {job.next_run_time}")
        if st.button("🛑 Stop Scheduler"):
            # logic to stop
            pass
    else:
        st.write("Scheduler Inactive")
        if st.button("🕒 Enable Daily Runs"):
            start_scheduler()
            st.rerun()

st.divider()
st.caption(f"Enterprise Arbitrage Engine v2.1 | Build {datetime.now().strftime('%Y%m%d')}")
