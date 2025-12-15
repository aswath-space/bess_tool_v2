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
import textwrap
from ui.progress_indicator import render_stage_header

from ui.css import get_tooltip_css
from ui.components import render_metric_card


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
    # ===================================================================
    # SUCCESS MESSAGE - Removed
    # ===================================================================
    # st.success("✅ PV Baseline Calculated Successfully!")
    
    # ===================================================================
    # KEY METRICS
    # ===================================================================
    st.markdown("### Performance Metrics")
    
    # Inject CSS for Tooltips
    st.markdown(get_tooltip_css(), unsafe_allow_html=True)
    
    # ===================================================================
    # METRICS ROW
    # ===================================================================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(render_metric_card(
            label="Annual Revenue (€)",
            value=f"{baseline_result['total_revenue_eur']:,.0f}",
            help_text="Total revenue from selling all PV generation at market prices"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(
            label="Generation (MWh)",
            value=f"{baseline_result['total_generation_mwh']:,.0f}",
            help_text="Total energy generated by the PV system per year"
        ), unsafe_allow_html=True)
    
    with col3:
        # Capture rate (KEY METRIC)
        capture_rate_pct = baseline_result['capture_rate'] * 100
        
        if capture_rate_pct > 80:
            delta_color = "normal"
            delta = "Healthy"
        elif capture_rate_pct > 70:
            delta_color = "off"
            delta = "Moderate"
        else:
            delta_color = "inverse"
            delta = "Low (<70%)"
        
        st.markdown(render_metric_card(
            label="Capture Rate",
            value=f"{capture_rate_pct:.1f}%",
            delta=delta,
            delta_color=delta_color,
            help_text="% of average market price captured (lower = more cannibalization). Lower is worse.",
            subtext=None # Removed to fix height consistency
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(render_metric_card(
            label="Avg Price (€/MWh)",
            value=f"{baseline_result['avg_revenue_per_mwh']:.1f}",
            help_text="Weighted average price received for your energy"
        ), unsafe_allow_html=True)
    
    # ===================================================================
    # CANNIBALIZATION CHART
    # ===================================================================
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("### Cannibalization Analysis")
    
    render_cannibalization_chart(baseline_result)
    
    # ===================================================================
    # CANNIBALIZATION EXPLANATION
    # ===================================================================
    # ===================================================================
    # CONSOLIDATED ANALYSIS BOX
    # ===================================================================
    
    # Calculate key data points
    cannib_loss_annual = baseline_result['cannibalization_loss_eur_annual']
    cannib_loss_per_mwh = baseline_result['cannibalization_loss_eur_mwh']
    negative_hours = baseline_result['negative_price_hours']
    negative_loss = baseline_result.get('negative_price_revenue_loss', 0)
    capture_rate_pct = baseline_result['capture_rate'] * 100
    
    # Recommendation Logic
    recommendation = baseline_service.should_recommend_battery(
        baseline_result,
        threshold=0.70
    )
    
    # Determine Status Color/Icon
    if capture_rate_pct < 70 or negative_hours > 100:
        box_style = "border: 1px solid rgba(245, 158, 11, 0.4); background-color: rgba(245, 158, 11, 0.05);" # Amber
        status_icon = "⚠️"
        status_title = "Optimization Opportunity Detected"
        text_color = "#d97706"
    else:
        box_style = "border: 1px solid rgba(16, 185, 129, 0.4); background-color: rgba(16, 185, 129, 0.05);" # Green
        status_icon = "✅"
        status_title = "Asset Performing Well"
        text_color = "#059669"

    # Build negative price section conditionally (to avoid nested f-strings)
    # IMPORTANT: No leading whitespace to prevent Streamlit from treating it as code
    negative_price_html = ""
    if negative_hours and negative_hours > 0:
        negative_price_html = f"""<div style="border-left: 3px solid #ef4444; padding-left: 1rem;">
<strong style="color: #b91c1c;">⚡ Negative Price Exposure</strong>
<p style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.95rem;">
Detected <strong>{negative_hours if negative_hours is not None else 0} hours</strong> of negative prices, resulting in <strong>€{negative_loss if negative_loss is not None else 0:,.0f}</strong> of potential revenue loss/curtailment.
</p>
</div>"""

    # Convert markdown in recommendation reason to HTML (since it's being used in HTML context)
    # The reason contains markdown like **text** which needs to be converted
    reason_text = recommendation['reason']
    # Replace markdown bold with HTML strong tags
    import re
    reason_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reason_text)
    # Replace newlines with <br> for proper HTML rendering
    reason_html = reason_html.replace('\n', '<br>')

    # Build the complete HTML string (all on fewer lines to avoid whitespace issues)
    html_content = f"""<div style="{box_style} padding: 1.5rem; border-radius: 12px; margin-top: 1rem; margin-bottom: 2rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
<h3 style="color: {text_color}; margin-top: 0; margin-bottom: 1rem; font-size: 1.25rem; display: flex; align-items: center;">
<span style="margin-right: 0.5rem; font-size: 1.5rem;">{status_icon}</span> {status_title}
</h3>
<div style="display: grid; grid-template-columns: 1fr; gap: 1rem;">
<div style="border-left: 3px solid {text_color}; padding-left: 1rem;">
<strong style="color: var(--text-main);">📉 Market Value Deflation</strong>
<p style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.95rem;">
Solar concentration during low-price hours is causing a <strong>capture rate erosion</strong> of <strong>€{cannib_loss_per_mwh:.1f}/MWh</strong> relative to baseload. Adding storage enables <em>price arbitrage</em> to recover this value.
</p>
</div>
{negative_price_html}
<div style="border-left: 3px solid {text_color}; padding-left: 1rem;">
<strong style="color: var(--text-main);">💡 Strategic Recommendation</strong>
<div style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.95rem;">
{reason_html}
</div>
</div>
</div>
</div>"""

    st.markdown(html_content, unsafe_allow_html=True)
    
    # CTA Button outside the box
    if recommendation['recommend']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("⚡ Analyze Battery Integration", type="primary", use_container_width=True):
                st.session_state.show_bess_inputs = True
                st.session_state.stage = 2
                st.rerun()
    else:
        if st.button("➕ Explore Battery Storage anyway"):
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
    
    # Trace 1: Baseload Price (Reference)
    # We show this as a single bar
    fig.add_trace(go.Bar(
        x=["Baseload Price<br>(Market Average)"],
        y=[baseload_price],
        name="Baseload Price",
        marker_color='#3b82f6',  # Blue
        text=[f"€{baseload_price:.1f}"],
        textposition='auto',
        hoverinfo='y+name'
    ))
    
    # Trace 2: Capture Price (What you get)
    # Stacked Trace A
    fig.add_trace(go.Bar(
        x=["Your Solar Capture"],
        y=[capture_price],
        name="Capture Price",
        marker_color='#10b981',  # Green (Money you get)
        text=[f"€{capture_price:.1f}"],
        textposition='auto',
        hoverinfo='y+name'
    ))
    
    # Trace 3: Cannibalization Loss (What you lost)
    # Stacked Trace B
    fig.add_trace(go.Bar(
        x=["Your Solar Capture"],
        y=[cannib_loss],
        name="Cannibalization Loss",
        marker_color='rgba(239, 68, 68, 0.6)',  # Red, semi-transparent
        text=[f"€{cannib_loss:.1f}"],
        textposition='auto',
        hoverinfo='y+name'
    ))
    
    # Update Layout for Stacking
    fig.update_layout(
        title="Solar Capture Rate vs. Baseload",
        barmode='stack', # Key change: Stack the bars
        yaxis_title="Price (€/MWh)",
        showlegend=True,
        height=400,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uniformtext_minsize=12, # Ensure text is readable
        uniformtext_mode='hide'
    )
    
    fig.update_traces(textfont_size=16) # Increase text size for all bars
    
    # Style y-axis
    fig.update_yaxes(gridcolor='#e2e8f0', gridwidth=1)
    
    # Display
    st.plotly_chart(fig, use_container_width=True)
