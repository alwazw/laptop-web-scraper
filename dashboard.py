import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_utils import (
    fetch_component_history, fetch_latest_listings, get_latest_component_prices,
    get_db_stats, fetch_execution_logs, get_historical_baseline, get_historical_avg,
    calculate_tev, CONDITION_MARKDOWN, load_scraper_config, save_scraper_config,
    calculate_triangulated_margin
)
from scheduler_utils import start_scheduler, get_jobs
import subprocess
import sys
import os
from datetime import datetime
import json

# --- Page Config ---
st.set_page_config(
    page_title="Arbitrage Command Center v2.2",
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
        # Group by product hash to find spreads between retailers
        for phash, group in latest_listings.groupby('product_hash'):
            # Dropshipping Logic (Triangulated TPS)
            retailers = group['source'].unique()
            if len(retailers) >= 2:
                for source in retailers:
                    for target in retailers:
                        if source == target: continue

                        source_listings = group[group['source'] == source]
                        target_listings = group[group['source'] == target]

                        buy_price = source_listings['listing_price'].max() # safety net: highest on source
                        lowest_target_price = target_listings['listing_price'].min()
                        tps = 0.95 * lowest_target_price
                        market_ref = get_historical_avg(phash, days=30) or lowest_target_price

                        net_profit, margin_pct_val, is_unrealistic = calculate_triangulated_margin(
                            buy_price=buy_price,
                            sell_price=tps,
                            market_ref_price=market_ref
                        )

                        if margin_pct_val > 10.0 and not is_unrealistic:
                            dropship_deals.append({
                                'title': group['listing_title'].iloc[0],
                                'source_site': source,
                                'source_price': buy_price,
                                'source_url': source_listings[source_listings['listing_price'] == buy_price]['url'].iloc[0],
                                'target_site': target,
                                'target_price': lowest_target_price,
                                'tps': tps,
                                'market_ref': market_ref,
                                'target_url': target_listings[target_listings['listing_price'] == lowest_target_price]['url'].iloc[0],
                                'margin_pct': margin_pct_val,
                                'profit': net_profit
                            })

        # Inventory Acquisition Logic (Outliers)
        for _, row in latest_listings.iterrows():
            hist_avg = get_historical_avg(row['product_hash'], days=30)
            if hist_avg:
                drop_pct = (hist_avg - row['listing_price']) / hist_avg
                if drop_pct >= 0.20:
                    inventory_deals.append({
                        'title': row['listing_title'],
                        'price': row['listing_price'],
                        'hist_avg': hist_avg,
                        'drop_pct': drop_pct * 100,
                        'source': row['source'],
                        'url': row['url']
                    })

    with col1:
        st.subheader("📦 Top Dropshipping Opportunities (Triangulated)")
        if dropship_deals:
            top_ds = sorted(dropship_deals, key=lambda x: x['margin_pct'], reverse=True)[:3]
            for deal in top_ds:
                with st.container():
                    st.markdown(f"""
                    <div class="opportunity-card">
                        <h4>{deal['title'][:60]}...</h4>
                        <p><b>Buy:</b> {deal['source_site']} @ ${deal['source_price']:.2f} | <b>Sell:</b> ${deal['tps']:.2f} (TPS)</p>
                        <p><b>Market Ref:</b> ${deal['market_ref']:.2f}</p>
                        <p><b>Net Profit:</b> ${deal['profit']:.2f} ({deal['margin_pct']:.1f}%)</p>
                    </div>
                    """, unsafe_allow_html=True)
                    lc1, lc2 = st.columns(2)
                    lc1.link_button("Source Listing", deal['source_url'], width='stretch')
                    lc2.link_button("Target Market", deal['target_url'], width='stretch')
        else:
            st.info("No high-confidence dropshipping spreads found.")

    with col2:
        st.subheader("🏢 Top Inventory Acquisitions (Outliers)")
        if inventory_deals:
            top_inv = sorted(inventory_deals, key=lambda x: x['drop_pct'], reverse=True)[:3]
            for deal in top_inv:
                with st.container():
                    st.markdown(f"""
                    <div class="opportunity-card" style="border-left-color: #00ff00;">
                        <h4>{deal['title'][:60]}...</h4>
                        <p><b>Current Price:</b> ${deal['price']:.2f}</p>
                        <p><b>30D Average:</b> ${deal['hist_avg']:.2f}</p>
                        <p><b>Liquidation:</b> {deal['drop_pct']:.1f}% below average</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.link_button("Acquire Unit", deal['url'], width='stretch')
        else:
            st.info("No significant price outliers detected.")

elif st.session_state.active_view == "Deal Hunter":
    st.title("🎯 Real-Time Arbitrage Engine")

    if latest_listings.empty:
        st.warning("No listings found. Run scraper.")
    else:
        # Strategy filtering
        processed = []
        for phash, group in latest_listings.groupby('product_hash'):
            hist_baseline = get_historical_baseline(phash)
            template_row = group.iloc[0]
            tev, harvest, chassis = calculate_tev(template_row, latest_components, hist_baseline)

            for _, row in group.iterrows():
                margin = tev - row['listing_price']
                margin_pct = (margin / row['listing_price']) * 100 if row['listing_price'] > 0 else 0

                other_retailers = group[group['source'] != row['source']]
                tps_margin = -100.0
                best_target = "N/A"
                if not other_retailers.empty:
                    lowest_target = other_retailers['listing_price'].min()
                    best_target = other_retailers[other_retailers['listing_price'] == lowest_target]['source'].iloc[0]
                    tps = 0.95 * lowest_target
                    _, tps_margin, _ = calculate_triangulated_margin(row['listing_price'], tps, lowest_target)

                show = False
                if enable_dropship and tps_margin >= 10.0: show = True
                if enable_inventory and margin_pct >= 10.0: show = True

                if show:
                    processed.append({
                        'id': row['id'],
                        'Retailer': row['source'],
                        'Title': row['listing_title'],
                        'Price': row['listing_price'],
                        'CPU Gen': row['cpu_gen'],
                        'Soldered': 'Y' if row['ram_soldered'] == 1 else 'N' if row['ram_soldered'] == 0 else '?',
                        'GPU': 'Y' if row['gpu_dedicated'] == 1 else 'N',
                        'Touch': 'Y' if row['is_touchscreen'] == 1 else 'N',
                        'TPS Margin %': round(tps_margin, 1) if tps_margin > -100 else 0,
                        'Inv Margin %': round(margin_pct, 1),
                        'Best Target': best_target,
                        'Method': 'Chassis' if hist_baseline else 'Harvest',
                        'row': row,
                        'harvest': harvest,
                        'chassis': chassis,
                        'tev': tev
                    })

        df_p = pd.DataFrame(processed)
        if not df_p.empty:
            st.dataframe(
                df_p[['Retailer', 'Title', 'Price', 'CPU Gen', 'Soldered', 'GPU', 'Touch', 'TPS Margin %', 'Inv Margin %', 'Best Target']],
                width='stretch',
                selection_mode="single-row",
                on_select="rerun",
                key="deal_table"
            )

            selected_rows = st.session_state.deal_table.get("selection", {}).get("rows", [])
            if selected_rows:
                idx = selected_rows[0]
                deal = processed[idx]
                st.divider()
                st.header("🔍 Opportunity Analysis")
                ac1, ac2 = st.columns(2)
                with ac1:
                    st.subheader("Valuation Breakdown")
                    st.write(f"**Calculated TEV:** ${deal['tev']:.2f}")
                    st.write(f"**Component Harvest Value:** ${deal['harvest']:.2f}")
                    st.write(f"**Condition-Adjusted Chassis:** ${deal['chassis']:.2f}")
                    st.info(f"Why relevant: This unit is priced at **${deal['Price']}**, which is **{deal['Inv Margin %']}%** below its intrinsic value.")
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

    st.subheader("Log Entry Details")
    if not df_logs.empty:
        selected_log_idx = st.selectbox("Select log entry to view metadata", df_logs.index, format_func=lambda x: f"{df_logs.loc[x, 'timestamp']} - {df_logs.loc[x, 'scraper_name']}")
        row = df_logs.loc[selected_log_idx]
        if row['metadata']:
            try:
                meta = json.loads(row['metadata'])
                st.json(meta)
            except:
                st.write(row['metadata'])

elif st.session_state.active_view == "Settings":
    st.title("⚙️ Scraper Configuration")
    config = load_scraper_config() or {
        "queries": ["laptop"],
        "sites": ["amazon", "bestbuy", "canadacomputers", "walmart", "staples", "dell", "hp"],
        "limit": 10,
        "schedule_time": "02:00",
        "brands": ["Dell", "HP", "Lenovo", "Apple"],
        "min_ram": "8GB",
        "min_ssd": "256GB"
    }

    with st.form("config_form"):
        col1, col2 = st.columns(2)
        with col1:
            queries = st.text_area("Base Search Queries", value=", ".join(config.get('queries', ['laptop'])))
            brands = st.multiselect("Preferred Brands", ["Dell", "HP", "Lenovo", "Apple", "Asus", "Acer", "MSI"], default=config.get('brands', []))
        with col2:
            min_ram = st.selectbox("Min RAM Filter", ["4GB", "8GB", "16GB", "32GB"], index=["4GB", "8GB", "16GB", "32GB"].index(config.get('min_ram', '8GB')))
            min_ssd = st.selectbox("Min SSD Filter", ["128GB", "256GB", "512GB", "1TB"], index=["128GB", "256GB", "512GB", "1TB"].index(config.get('min_ssd', '256GB')))

        sites = st.multiselect("Target Sites", ["amazon", "bestbuy", "canadacomputers", "walmart", "staples", "dell", "hp"], default=config['sites'])
        limit = st.number_input("Limit per site", value=config['limit'])
        sched = st.time_input("Recurring Daily Run", value=datetime.strptime(config['schedule_time'], "%H:%M").time())

        c1, c2 = st.columns(2)
        save_btn = c1.form_submit_button("💾 Save Config Only")
        run_btn = c2.form_submit_button("🚀 Run Immediate Search")

        if save_btn or run_btn:
            new_config = {
                "queries": [q.strip() for q in queries.split(",")],
                "brands": brands,
                "min_ram": min_ram,
                "min_ssd": min_ssd,
                "sites": sites,
                "limit": limit,
                "schedule_time": sched.strftime("%H:%M")
            }
            save_scraper_config(new_config)
            st.success("Configuration saved!")
            if run_btn:
                subprocess.run([sys.executable, "main.py"])
                st.rerun()

st.divider()
st.caption(f"Enterprise Arbitrage Engine v2.2 | Build {datetime.now().strftime('%Y%m%d')}")
