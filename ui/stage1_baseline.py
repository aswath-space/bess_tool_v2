"""
Stage 1: PV Baseline Component
===============================

This component implements "The Anchor" stage of the user journey.
It collects PV configuration inputs and displays the baseline revenue
that a PV-only system would generate WITHOUT battery storage.

Purpose:
--------
Establish the baseline so users can later see the INCREMENTAL value
of adding battery storage. This creates the "aha moment" when they
realize how much revenue is being lost to cannibalization.

Key Outputs:
------------
1. Baseline Revenue (EUR/year)
2. Cannibalization Analysis (Capture Rate %)
3. Negative Price Exposure
4. Recommendation whether to add battery

User Flow:
----------
1. User enters location and PV configuration
2. Clicks "Calculate PV Baseline"
3. System shows baseline results and cannibalization chart
4. If capture rate < 70%, highlight battery recommendation
5. "Add Battery Storage" button appears to move to Stage 2

Author: Aswath
Date: 2025-12-11
"""

import streamlit as st
import plotly.graph_objects as go
from backend.app.services.baseline_service import baseline_service
from backend.app.services.entsoe_service import entsoe_service
from backend.app.services.pv_service import pv_service
import pandas as pd
from ui.progress_indicator import render_stage_header


def render_stage1_inputs():
    """
    Render input form for PV baseline configuration.
    
    Collects:
    - Location (lat/lon)
    - PV capacity (MW)
    - PV orientation (tilt, azimuth)
    - PV CAPEX (EUR/Wp)
    
    Returns:
    --------
    dict
        Configuration dictionary with all PV parameters
        
    Example:
    --------
    >>> config = render_stage1_inputs()
    >>> # User fills in form and values are returned in config dict
    """
    
    st.markdown("### Solar Park Configuration")
    
    # ===================================================================
    # LOCATION INPUT WITH GEOPY
    # ===================================================================
    with st.expander("Configure PV System Parameters", expanded=True):
        # City search with geopy
        st.markdown("#### Location")
        
        city_search = st.text_input(
            "Search by City (optional)",
            placeholder="e.g., Berlin, Germany",
            help="Enter city name to auto-fill coordinates below"
        )
        
        if city_search:
            if st.button("🔍 Find Location", key="city_search_btn"):
                try:
                    from geopy.geocoders import Nominatim
                    geolocator = Nominatim(user_agent="pv_bess_tool")
                    location = geolocator.geocode(city_search)
                    
                    if location:
                        st.session_state.search_lat = location.latitude
                        st.session_state.search_lon = location.longitude
                        st.success(f"✓ Found: {location.address}")
                    else:
                        st.error("Location not found. Try a different query.")
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")
        
        st.markdown("---")
        st.caption("Coordinates (from search or enter manually)")
        
        # Two-column layout
        col_left, col_right = st.columns(2)
        
        # LEFT COLUMN: Latitude, Size, Orientation
        with col_left:
            # 1. Latitude
            lat = st.number_input(
                "Latitude (°)",
                value=st.session_state.get('search_lat', 52.5200),
                format="%.4f",
                help="Decimal degrees"
            )
            
            st.markdown("#### PV System Size")
            
            # 2. PV Capacity
            # Typical utility-scale: 5-50 MW
            pv_capacity = st.number_input(
                "PV Capacity (MW)",
                value=10.0,
                step=0.5,
                min_value=0.1,
                help="Nameplate capacity of the solar park in megawatts"
            )
            
            st.markdown("#### PV Orientation")
            st.caption("These affect how much energy you generate")
            
            # 3. Tilt Angle
            pv_tilt = st.slider(
                "Tilt Angle (°)",
                min_value=0.0,
                max_value=90.0,
                value=35.0,  # Good for Central Europe
                help="0° = horizontal, 90° = vertical. Optimal ≈ latitude"
            )
            
            # 4. Azimuth
            pv_azimuth = st.slider(
                "Azimuth (°)",
                min_value=-180.0,
                max_value=180.0,
                value=0.0,  # South-facing
                help="0° = South, 90° = West, -90° = East"
            )
        
        # RIGHT COLUMN: Longitude, Economics
        with col_right:
            # 1. Longitude
            lon = st.number_input(
                "Longitude (°)",
                value=st.session_state.get('search_lon', 13.4050),
                format="%.4f",
                help="Decimal degrees"
            )
            
            st.markdown("#### Economics")
            
            # 2. Project Type
            project_type = st.selectbox(
                "Project Type",
                options=["Greenfield", "Brownfield"],
                index=0,
                help="Greenfield = New PV+BESS project | Brownfield = Adding BESS to existing PV"
            )
            
            # 3. PV System Age (only for Brownfield)
            pv_age_years = 0
            if project_type == "Brownfield":
                pv_age_years = st.number_input(
                    "PV System Age (Years)",
                    value=0,
                    min_value=0,
                    max_value=30,
                    step=1,
                    help="Age of existing PV system when adding battery (used for depreciation)"
                )
                
                # Validation warning for old systems
                if pv_age_years > 20:
                    st.warning(f"""
                    ⚠️ PV system is {pv_age_years} years old. 
                    Battery lifetime may extend beyond typical PV lifespan (25 years).
                    Consider PV refurbishment or shortened analysis period.
                    """)
            
            # 4. PV Cost (CAPEX)
            pv_cost = st.number_input(
                "PV Cost (€/Wp)" + (" (historical CAPEX)" if project_type == "Brownfield" else ""),
                value=0.60,
                step=0.05,
                min_value=0.1,
                help="Fully installed cost per Watt-peak" + (
                    " - original cost for depreciation calc" if project_type == "Brownfield" 
                    else " (typical: €0.50-0.80/Wp)"
                )
            )
    
    # Use columns to center the button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calculate_baseline = st.button(
            "Calculate Baseline",
            type="primary",
            use_container_width=True
        )
    
    # ===================================================================
    # RETURN CONFIGURATION
    # ===================================================================
    return {
        'lat': lat,
        'lon': lon,
        'capacity_mw': pv_capacity,  # Changed from 'pv_capacity_mw' to match financial_service
        'pv_capacity_mw': pv_capacity,  # Keep for backwards compatibility
        'pv_tilt': pv_tilt,
        'pv_azimuth': pv_azimuth,
        'cost_eur_wp': pv_cost,  # Changed from 'pv_cost_eur_wp' to match financial_service
        'project_type': project_type,  # NEW: Greenfield or Brownfield
        'pv_age_years': pv_age_years  # NEW: Age for brownfield projects
    }, calculate_baseline


def render_stage1_results(baseline_result, config):
    """
    Display PV baseline results with cannibalization analysis.
    
    Shows:
    - Key metrics (revenue, generation, capture rate)
    - Cannibalization chart (capture price vs baseload)
    - Negative price exposure
    - Battery recommendation if capture rate < 70%
    
    Parameters:
    -----------
    baseline_result : dict
        Result from baseline_service.calculate_pv_baseline()
    config : dict
        Original PV configuration for reference
    """
    
    # ===================================================================
    # SUCCESS MESSAGE
    # ===================================================================
    st.success("✅ PV Baseline Calculated Successfully!")
    
    # ===================================================================
    # KEY METRICS
    # ===================================================================
    st.markdown("### Performance Metrics")
    
    # Create four columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Total annual revenue
        st.metric(
            "Annual Revenue",
            f"€{baseline_result['total_revenue_eur']:,.0f}",
            help="Total revenue from selling all PV generation at market prices"
        )
    
    with col2:
        # Total generation
        st.metric(
            "Annual Generation",
            f"{baseline_result['total_generation_mwh']:,.0f} MWh",
            help="Total energy generated by the PV system per year"
        )
    
    with col3:
        # Capture rate (KEY METRIC)
        capture_rate_pct = baseline_result['capture_rate'] * 100
        
        # Color code based on capture rate
        # >80% = Good, 70-80% = OK, <70% = Poor (needs battery)
        if capture_rate_pct > 80:
            delta_color = "normal"
            delta = "Healthy"
        elif capture_rate_pct > 70:
            delta_color = "off"
            delta = "Moderate"
        else:
            delta_color = "inverse"
            delta = "Low - Battery Recommended"
        
        st.metric(
            "Capture Rate",
            f"{capture_rate_pct:.1f}%",
            delta=delta,
            delta_color=delta_color,
            help="% of average market price captured (lower = more cannibalization)"
        )
    
    with col4:
        # Average revenue per MWh
        st.metric(
            "Avg Price Received",
            f"€{baseline_result['avg_revenue_per_mwh']:.1f}/MWh",
            help="Weighted average price received for your energy"
        )
    
    # ===================================================================
    # CANNIBALIZATION CHART
    # ===================================================================
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("### Cannibalization Analysis")
    
    render_cannibalization_chart(baseline_result)
    
    # ===================================================================
    # CANNIBALIZATION EXPLANATION
    # ===================================================================
    # Calculate cannibal loss metrics
    cannib_loss_annual = baseline_result['cannibalization_loss_eur_annual']
    cannib_loss_per_mwh = baseline_result['cannibalization_loss_eur_mwh']
    
    # Show concise explanation
    if cannib_loss_annual > 0:
        st.caption(f"""
        **Solar generation peaks during low-price hours, reducing average revenue by 
        €{cannib_loss_per_mwh:.1f}/MWh (€{cannib_loss_annual:,.0f}/year). 
        Battery storage enables price arbitrage to recover losses.**
        """)
    
    # ===================================================================
    # NEGATIVE PRICE HANDLING
    # ===================================================================
    if baseline_result['negative_price_hours'] > 0:
        st.caption(f"""
        ⚠️ **{baseline_result['negative_price_hours']} hours of negative prices detected** — 
        Estimated loss: €{baseline_result['negative_price_revenue_loss']:,.0f}. 
        Battery storage eliminates curtailment losses.
        """)
    
    # ===================================================================
    # BATTERY RECOMMENDATION
    # ===================================================================
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    recommendation = baseline_service.should_recommend_battery(
        baseline_result,
        threshold=0.70  # User-specified 70% threshold
    )
    
    if recommendation['recommend']:
        st.warning(recommendation['reason'])
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            add_battery = st.button(
                "⚡ Add Battery Storage",
                type="primary",
                use_container_width=True
            )
            
            if add_battery:
                st.session_state.show_bess_inputs = True
                st.session_state.stage = 2
                st.rerun()
    else:
        st.success(recommendation['reason'])
        
        if st.button("➕ Explore Battery Storage"):
            st.session_state.show_bess_inputs = True
            st.session_state.stage = 2
            st.rerun()


def render_cannibalization_chart(baseline_result):
    """
    Create a bar chart showing capture price vs baseload price.
    
    This visualization clearly shows the cannibalization effect:
    - Blue bar: What a 24/7 baseload plant would get (average price)
    - Red bar: What solar actually gets (weighted by generation)
    - Gap: Money lost due to solar's midday profile
    
    Parameters:
    -----------
    baseline_result : dict
        Baseline calculation results with price metrics
    """
    
    # Extract prices
    baseload_price = baseline_result['overall_avg_price']
    capture_price = baseline_result['weighted_avg_price']
    cannib_loss = baseline_result['cannibalization_loss_eur_mwh']
    
    # Create figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=["Baseload Price<br>(24/7 average)", "Your Capture Price<br>(solar weighted)"],
        y=[baseload_price, capture_price],
        marker_color=['#3b82f6', '#ef4444'],  # Blue and Red
        text=[
            f"€{baseload_price:.1f}/MWh",
            f"€{capture_price:.1f}/MWh"
        ],
        textposition='outside',
        textfont=dict(size=14, weight='bold')
    ))
    
    # Add annotation showing the gap
    fig.add_annotation(
        x=0.5,
        y=max(baseload_price, capture_price) * 0.6,
        text=f"<b>Cannibalization Loss</b><br>€{cannib_loss:.1f}/MWh",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor="#ef4444",
        font=dict(size=13, color="#ef4444"),
        bgcolor="rgba(239, 68, 68, 0.1)",
        bordercolor="#ef4444",
        borderwidth=2,
        borderpad=10
    )
    
    # Layout
    fig.update_layout(
        title="Capture Price vs. Baseload Price",
        yaxis_title="Price (€/MWh)",
        showlegend=False,
        height=400,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Style y-axis
    fig.update_yaxes(gridcolor='#e2e8f0', gridwidth=1)
    
    # Display
    st.plotly_chart(fig, use_container_width=True)
