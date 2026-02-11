import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_utils import fetch_component_history, fetch_latest_listings, get_latest_component_prices, get_db_stats
from scheduler_utils import start_scheduler, get_jobs
import subprocess
import sys
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Laptop Arbitrage Command Center",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a slick look
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3e4451;
    }
    .stDataFrame {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🎛️ Control Panel")
mode = st.sidebar.selectbox("Dashboard Mode", ["Market Pulse", "Deal Hunter", "Scraper Management"])

st.sidebar.divider()

# --- Functions to trigger scripts ---
def run_scraper(script_name, args=None):
    with st.spinner(f"Running {script_name}..."):
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            st.sidebar.success(f"{script_name} completed!")
            return result.stdout
        else:
            st.sidebar.error(f"{script_name} failed!")
            return result.stderr

if st.sidebar.button("🚀 Run Full Pipeline"):
    out = run_scraper("main.py")
    st.sidebar.text_area("Logs", out, height=200)

if st.sidebar.button("🧹 Initialize DB"):
    run_scraper("db_setup.py")

st.sidebar.divider()
st.sidebar.info("System Status: Online 🟢")

# --- Main Content ---
st.title("💻 Laptop Arbitrage Command Center")

stats = get_db_stats()

# Top Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Listings", stats['total_listings'])
m2.metric("Unique Products", stats['total_products'])
m3.metric("Components Tracked", stats['tracked_components'])
m4.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

# --- Owner's Insight ---
with st.expander("🤖 Project Owner's Intelligence Report"):
    st.markdown("""
    **Current Market Analysis:**
    - **RAM Trends:** DDR4 prices are stabilizing, but DDR5 shows high volatility. Recommend focusing on DDR4 laptops for consistent margins.
    - **Arbitrage Opportunity:** High supply of 'OpenBox' units on BestBuy is creating a price floor. Amazon remains the best place for 'New' resale.
    - **Strategy:** Look for laptops with < 16GB RAM; they often have the highest 'upgrade-to-resale' value.
    """)

if mode == "Market Pulse":
    st.header("📈 Market Pulse")
    df_history = fetch_component_history()

    if not df_history.empty:
        col1, col2 = st.columns([3, 1])

        with col1:
            # Component Type Filter
            comp_types = st.multiselect("Filter Components", df_history['component_key'].unique(), default=df_history['component_key'].unique()[:5])
            df_filtered = df_history[df_history['component_key'].isin(comp_types)]

            fig = px.line(df_filtered, x='report_date', y='avg_price', color='component_key',
                         title="Component Price Trends (CAD)",
                         labels={'avg_price': 'Price ($)', 'report_date': 'Date'},
                         markers=True, template="plotly_dark")
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Latest Averages")
            latest_prices = get_latest_component_prices()
            for key, price in latest_prices.items():
                st.metric(label=key.replace('_', ' '), value=f"${price:.2f}")
    else:
        st.warning("No component history found. Please run the Component Scraper.")

elif mode == "Deal Hunter":
    st.header("🎯 Deal Hunter")

    # Advanced Search in Sidebar
    st.sidebar.subheader("Deal Filters")
    min_ram = st.sidebar.select_slider("Min RAM", options=['4GB', '8GB', '16GB', '32GB'], value='8GB')
    min_ssd = st.sidebar.select_slider("Min SSD", options=['128GB', '256GB', '512GB', '1TB'], value='256GB')

    df_listings = fetch_latest_listings()
    latest_components = get_latest_component_prices()

    if not df_listings.empty:
        # Calculate Scrap Value
        def calculate_scrap(row):
            val = 0
            # RAM
            ram_key = f"RAM_{row['ram_spec_type'] or 'DDR4'}_{row['ram_spec_capacity'] or '8GB'}".replace(' ', '')
            val += latest_components.get(ram_key, 50.0) # Fallback to $50 if unknown
            # SSD
            ssd_key = f"SSD_NVMe_{row['ssd_spec_capacity'] or '256GB'}".replace(' ', '')
            val += latest_components.get(ssd_key, 60.0) # Fallback to $60 if unknown
            # Base chassis value (approximate)
            val += 200.0 if "i7" in str(row['cpu_model']).lower() or "Ryzen 7" in str(row['cpu_model']) else 100.0
            return val

        df_listings['Estimated_Value'] = df_listings.apply(calculate_scrap, axis=1)
        df_listings['Arbitrage'] = df_listings['Estimated_Value'] - df_listings['listing_price']

        # Search & Filters
        search = st.text_input("🔍 Search listings (Brand, CPU, Title...)", "")
        col1, col2, col3 = st.columns(3)
        with col1:
            site_filter = st.multiselect("Source", df_listings['source'].unique(), default=df_listings['source'].unique())
        with col2:
            price_range = st.slider("Price Range ($)", 0.0, float(df_listings['listing_price'].max()), (0.0, float(df_listings['listing_price'].max())))
        with col3:
            min_arbitrage = st.number_input("Min Arbitrage ($)", value=0.0)

        # Apply filters
        df_display = df_listings[
            (df_listings['listing_title'].str.contains(search, case=False)) &
            (df_listings['source'].isin(site_filter)) &
            (df_listings['listing_price'].between(price_range[0], price_range[1])) &
            (df_listings['Arbitrage'] >= min_arbitrage)
        ]

        # Sort by Arbitrage
        df_display = df_display.sort_values(by='Arbitrage', ascending=False)

        # Display with highlighting
        st.dataframe(df_display.style.highlight_max(subset=['Arbitrage'], color='#004d00'), use_container_width=True)

        if not df_display.empty:
            st.success(f"Found {len(df_display)} potential deals!")
            best_deal = df_display.iloc[0]
            st.info(f"💡 **Top Deal:** {best_deal['listing_title']} at **${best_deal['listing_price']}** (Est. Value: ${best_deal['Estimated_Value']:.2f})")
    else:
        st.warning("No listings found. Please run the Laptop Scraper.")

elif mode == "Scraper Management":
    st.header("⚙️ Scraper Management")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Manual Runs")
        if st.button("Run Component Scraper"):
            run_scraper("scraper_components.py")
        if st.button("Run Laptop Scraper (Demo)"):
            run_scraper("scraper_laptops.py", ["--mode", "demo"])
        if st.button("Run Laptop Scraper (Live - 1 limit)"):
            run_scraper("scraper_laptops.py", ["--mode", "live", "--limit", "1", "--sites", "amazon"])

    with col2:
        st.subheader("Scheduling")
        jobs = get_jobs()
        if jobs:
            for job in jobs:
                st.write(f"✅ **Job:** {job.id} | **Next run:** {job.next_run_time}")
        else:
            st.write("Current Schedule: Not Configured")

        if st.button("Enable Daily Runs (2 AM)"):
            start_scheduler()
            st.success("Background scheduler started!")
            st.rerun()

st.divider()
st.caption("v1.0.0-Beta | Built for Canadian Arbitrage")
