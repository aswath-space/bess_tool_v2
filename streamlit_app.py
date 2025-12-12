"""
Main Streamlit Application - PV-BESS Investor Guide
====================================================

This is the main entry point for the application. It implements a
progressive disclosure single-page flow through three stages:

Stage 1: PV Baseline (The Anchor)
- Establish baseline revenue without battery
- Show cannibalization effect
- Recommend battery if capture rate < 70%

Stage 2: Battery Solution (The Upsell)
- Smart battery sizing defaults (40% of PV)
- LP optimization for revenue maximization
- Value bridge waterfall chart

Stage 3: Investment Decision (The Decision)
- IRR, NPV, payback calculations
- Real-time sensitivity sliders
- Greenfield vs brownfield scenarios

Key Features:
-------------
- Single-page UX (no navigation needed)
- Progressive disclosure (stages reveal as user progresses)
- Real-time parameter adjustments
- All results stay visible for comparison

Session State Management:
-------------------------
st.session_state tracks:
- stage: Current stage number (1, 2, or 3)
- show_bess_inputs: Whether to show Stage 2
- baseline_result: Stage 1 results
- optimization_result: Stage 2 results
- pv_config: PV configuration
- bess_config: Battery configuration

Author: Aswath
Date: 2025-12-11
"""

import streamlit as st
import pandas as pd
import json
import zipfile
import io
from datetime import datetime
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ===================================================================
# SETUP
# ===================================================================
# Load environment variables - Streamlit secrets take precedence
# For local dev: use .streamlit/secrets.toml
# For Streamlit Cloud: configure in app settings
if hasattr(st, 'secrets') and 'entsoe' in st.secrets:
    os.environ['ENTSOE_API_KEY'] = st.secrets['entsoe']['api_key']
else:
    # Fallback to .env file for local development
    load_dotenv('backend/entso.env')

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# ===================================================================
# IMPORTS - Backend Services
# ===================================================================
try:
    from app.services.entsoe_service import entsoe_service
    from app.services.pv_service import pv_service
    from app.services.baseline_service import baseline_service
    from app.services.optimization_service import optimization_service
except ImportError as e:
    st.error(f"Critical Error: Could not import backend services. {e}")
    st.stop()

# ===================================================================
# IMPORTS - UI Components
# ===================================================================
from ui.progress_indicator import render_progress_indicator
from ui.stage1_baseline import render_stage1_inputs, render_stage1_results
from ui.stage2_battery import render_stage2_inputs, render_stage2_results
from ui.stage3_investment import render_stage3
from ui.css import load_css

# ===================================================================
# PAGE CONFIGURATION
# ===================================================================
st.set_page_config(
    page_title="PV-BESS Revenue Optimization",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar completely
)

# Hide Streamlit branding and sidebar
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# Load custom CSS
load_css("assets/style.css")
# Trigger reload

# ===================================================================
# NAVIGATION ROUTING
# ===================================================================
# Handle query parameters for multi-page feel in single-page app
# Support newer st.query_params (1.30+) and fallback if needed
try:
    query_params = st.query_params
except AttributeError:
    query_params = st.experimental_get_query_params()

if "page" in query_params:
    page = query_params["page"]
    if isinstance(page, list): page = page[0]  # Handle list return from experimental
    
    if page == "theory":
        from ui.explainer_page import render_explainer_page
        render_explainer_page()
        st.markdown("---")
        if st.button("← Back to App"):
            st.query_params.clear()
            st.rerun()
        st.stop()
        
    elif page == "credits":
        from ui.info_pages import render_credits_page
        render_credits_page()
        st.stop()
        
    elif page == "coverage":
        from ui.info_pages import render_coverage_page
        render_coverage_page()
        st.stop()

# ===================================================================
# SESSION STATE INITIALIZATION
# ===================================================================
# Initialize session state variables if they don't exist
if 'stage' not in st.session_state:
    st.session_state.stage = 1  # Start at Stage 1: PV Baseline

if 'show_bess_inputs' not in st.session_state:
    st.session_state.show_bess_inputs = False  # Don't show Stage 2 initially

if 'baseline_result' not in st.session_state:
    st.session_state.baseline_result = None

if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = None

if 'pv_config' not in st.session_state:
    st.session_state.pv_config = None

if 'bess_config' not in st.session_state:
    st.session_state.bess_config = None

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================
def clear_cache_and_reset():
    """Clear cached data files and reset session state."""
    import glob
    import shutil
    
    # Clear cached price files
    cache_dir = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'cache')
    if os.path.exists(cache_dir):
        cache_files = glob.glob(os.path.join(cache_dir, '*.csv'))
        for file in cache_files:
            try:
                os.remove(file)
            except Exception as e:
                print(f"Could not delete {file}: {e}")
    
    # Clear all session state variables
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# ===================================================================
# HEADER WITH DOWNLOAD BUTTON
# ===================================================================
# ===================================================================
# HEADER
# ===================================================================
col_title, col_download = st.columns([5, 1])

with col_title:
    st.title("⚡ PV-BESS Revenue Optimization")
    st.markdown("""
    <div style="padding: 1.25rem; background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(16, 185, 129, 0.05)); 
    border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #3b82f6;">
        <p style="margin: 0; color: #475569; font-size: 1rem; line-height: 1.6;">
            Quantify revenue potential for solar + battery storage assets using real market data.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ===================================================================
# STAGE 1: PV BASELINE (Always Visible)
# ===================================================================
# This stage is always shown - it's the starting point

# Render inputs
pv_config, calculate_baseline = render_stage1_inputs()

# Store PV config in session state
st.session_state.pv_config = pv_config

# Handle baseline calculation
if calculate_baseline:
    with st.spinner("📡 Fetching Data & Calculating PV Baseline..."):
        try:
            # ===========================
            # STEP 1: Determine Analysis Period (Last Complete 12 Months)
            # ===========================
            # Example: If today is Dec 12, 2025 -> Period is Dec 1, 2024 to Nov 30, 2025
            today = pd.Timestamp.now(tz='UTC')
            start_of_current_month = today.replace(day=1).normalize()
            
            # End Date = Last moment of the previous month
            end_date = start_of_current_month - pd.Timedelta(seconds=1)
            
            # Start Date = 1 year before the start of current month (to get exactly 12 months)
            # e.g. Dec 1 2024
            start_date = start_of_current_month - pd.DateOffset(years=1)
            
            # Store date info in session state for charts
            st.session_state.analysis_start_date = start_date
            st.session_state.analysis_end_date = end_date
            
            st.info(f"📅 Analysis Period: **{start_date.strftime('%Y-%m-%d')}** to **{end_date.strftime('%Y-%m-%d')}**")
            
            # ===========================
            # STEP 2: Fetch Market Data
            # ===========================
            # Determine market zone from coordinates
            zone = entsoe_service.get_zone_from_lat_lon(pv_config['lat'], pv_config['lon'])
            if not zone:
                st.warning(f"Could not determine ENTSO-E zone for coordinates. Defaulting to 'DE_LU' (Germany).")
                zone = "DE_LU"
            else:
                st.info(f"Detected Market Zone: **{zone}**")
            
            # Fetch day-ahead prices
            status_placeholder = st.empty()
            status_placeholder.text("Fetching Day-Ahead Market Prices...")
            
            prices_df = entsoe_service.fetch_day_ahead_prices(zone, start_date, end_date)
            price_data = prices_df.reset_index().rename(
                columns={'index': 'timestamp', 'price': 'price'}
            ).to_dict(orient='records')
            
            # ===========================
            # STEP 3: Fetch PV Data
            # ===========================
            status_placeholder.text("Simulating PV Generation (PVGIS)...")
            
            # Pass explicit dates to Open-Meteo
            pv_df = pv_service.fetch_pv_generation(
                lat=pv_config['lat'],
                lon=pv_config['lon'],
                peak_power_kw=pv_config['pv_capacity_mw'] * 1000,
                loss=14.0,  # Default system losses
                tilt=pv_config['pv_tilt'],
                azimuth=pv_config['pv_azimuth'],
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            # ===========================
            # STEP 3: Calculate Baseline
            # ===========================
            status_placeholder.text("Calculating PV Baseline Metrics...")
            
            baseline_result = baseline_service.calculate_pv_baseline(
                pv_df=pv_df,
                price_data=price_data
            )
            
            # Store results in session state
            st.session_state.baseline_result = baseline_result
            st.session_state.price_data = price_data  # List of dicts for optimization service
            st.session_state.prices_df = prices_df  # DataFrame for CSV download
            st.session_state.pv_df = pv_df
            
            status_placeholder.empty()
            status_placeholder.empty()
            # st.success("✅ Analysis complete") - Removed per user request
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.stop()

# Display baseline results if available
if st.session_state.baseline_result is not None:
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    render_stage1_results(
        baseline_result=st.session_state.baseline_result,
        config=pv_config
    )

# ===================================================================
# STAGE 2: BATTERY SOLUTION (Conditional Display)
# ===================================================================
# Only show if user clicked "Add Battery Storage" in Stage 1

if st.session_state.show_bess_inputs and st.session_state.baseline_result is not None:
    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)
    
    # Render battery inputs
    bess_config, optimize_button = render_stage2_inputs(
        pv_capacity_mw=pv_config['pv_capacity_mw']
    )
    
    # Store BESS config
    st.session_state.bess_config = bess_config
    
    # Handle optimization
    if optimize_button:
        with st.spinner("⚡ Optimizing..."):
            try:
                # Run CVXPY optimization
                optimization_result = optimization_service.run_optimization(
                    pv_df=st.session_state.pv_df,
                    price_data=st.session_state.price_data,
                    bess_power_mw=bess_config['power_mw'],
                    bess_capacity_mwh=bess_config['capacity_mwh']
                )
                
                # Store results
                st.session_state.optimization_result = optimization_result
                st.session_state.stage = 3  # Move to Stage 3
                
                # Success feedback - Removed per user request
                # st.balloons() 
                # st.success("✅ Battery optimization complete! Your revenue has been maximized.")
                
            except Exception as e:
                st.error(f"Optimization failed: {str(e)}")
                st.error("Please check your battery configuration and try again.")
    
    # Display optimization results if available
    if st.session_state.optimization_result is not None:
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
        
        render_stage2_results(
            optimization_result=st.session_state.optimization_result,
            baseline_result=st.session_state.baseline_result,
            analysis_start_date=st.session_state.get('analysis_start_date')
        )

# ===================================================================
# STAGE 3: INVESTMENT DECISION (Conditional Display)
# ===================================================================
# Only show if optimization is complete

if (st.session_state.stage >= 3 and 
    st.session_state.optimization_result is not None and
    st.session_state.baseline_result is not None):
    
    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)
    
    render_stage3(
        optimization_result=st.session_state.optimization_result,
        baseline_result=st.session_state.baseline_result,
        pv_config=st.session_state.pv_config,
        bess_config=st.session_state.bess_config
    )

# ===================================================================
# EMPTY STATE (If No Data Yet)
# ===================================================================
if st.session_state.baseline_result is None:
    st.info("👆 Configure your solar park parameters above and click 'Calculate PV Baseline' to begin.")


# ===================================================================
# CUSTOM FOOTER
# ===================================================================
# ===================================================================
# EXPORT & RESET (Bottom Section)
# ===================================================================
# Only show if there are results
if st.session_state.baseline_result is not None:
    st.markdown("---")
    st.markdown("### 📥 Export Values & Reset")
    
    col_export_1, col_export_2, col_spacer = st.columns([1, 1, 3])
    
    with col_export_1:
         # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # 1. Electricity Prices CSV
            if 'prices_df' in st.session_state and st.session_state.prices_df is not None:
                prices_csv = st.session_state.prices_df.to_csv(index=True)
                zip_file.writestr('electricity_prices.csv', prices_csv)
            
            # 2. PV Production CSV
            if 'pv_df' in st.session_state and st.session_state.pv_df is not None:
                pv_csv = st.session_state.pv_df.to_csv(index=True)
                zip_file.writestr('pv_production.csv', pv_csv)
            
            # 3. Summary JSON
            summary = {
                'timestamp': datetime.now().isoformat(),
                'pv_config': st.session_state.get('pv_config', {}),
                'baseline_metrics': {
                    'annual_revenue_eur': st.session_state.baseline_result.get('total_revenue_eur'),
                    'annual_generation_mwh': st.session_state.baseline_result.get('total_generation_mwh'),
                    'capture_rate': st.session_state.baseline_result.get('capture_rate'),
                    'cannibalization_loss_eur': st.session_state.baseline_result.get('cannibalization_loss_eur_annual')
                }
            }
            
            if st.session_state.get('optimization_result'):
                summary['bess_config'] = st.session_state.get('bess_config', {})
                summary['optimization_metrics'] = {
                    'optimized_revenue_eur': st.session_state.optimization_result['financials'].get('total_revenue_eur'),
                    'revenue_increase_eur': st.session_state.optimization_result['financials'].get('total_revenue_eur') - st.session_state.baseline_result.get('total_revenue_eur')
                }
            
            zip_file.writestr('analysis_summary.json', json.dumps(summary, indent=2, default=str))
        
        zip_buffer.seek(0)
        
        st.download_button(
            label="📥 Download Data",
            data=zip_buffer,
            file_name=f"pv_bess_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
            help="Download all source data and analysis results"
        )
        
    with col_export_2:
        if st.button(
            "🔄 Reset Analysis",
            use_container_width=True,
            help="Clear all data and start over",
            type="secondary"
        ):
            clear_cache_and_reset()
            st.rerun()

st.markdown("---")
st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

# Simple footer using columns
footer_col1, footer_col2, footer_col3 = st.columns([1, 1, 1])

with footer_col1:
    # Use HTML links with target="_self" to force reload with query param
    st.markdown("""
    <a href="/?page=theory" target="_self" style="text-decoration: none; color: #4b5563;">📚 Theory</a> • 
    <a href="/?page=credits" target="_self" style="text-decoration: none; color: #4b5563;">Credits</a> • 
    <a href="/?page=coverage" target="_self" style="text-decoration: none; color: #4b5563;">Coverage</a>
    """, unsafe_allow_html=True)

with footer_col2:
    st.markdown("""
    <p style='text-align: center; margin: 0; color: #64748b; font-size: 0.9rem;'>
        Hosted with <a href='https://streamlit.io' target='_blank' style='color: #ff4b4b; text-decoration: none;'>Streamlit</a>
    </p>
    """, unsafe_allow_html=True)

with footer_col3:
    st.markdown("""
    <p style='text-align: right; margin: 0; color: #94a3b8; font-size: 0.85rem;'>
        © 2025 Aswath
    </p>
    """, unsafe_allow_html=True)
