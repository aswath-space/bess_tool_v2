"""
Stage 2: Battery Solution Component
====================================

This component implements "The Upsell" stage of the user journey.
It shows the INCREMENTAL value of adding battery storage to the PV system.

Purpose:
--------
Demonstrate that battery storage can recover the cannibalization losses
shown in Stage 1 AND generate additional arbitrage revenue. This is the
key "value proposition" that convinces investors.

Key Outputs:
------------
1. Value Bridge Waterfall Chart (Base PV + Arbitrage + Recovery)
2. Optimized battery dispatch schedule
3. Operations timeline showing when battery charges/discharges
4. Battery utilization metrics

User Flow:
----------
1. System suggests smart defaults (40% of PV capacity, 4h duration)
2. User can accept defaults or customize battery sizing
3. User can expand "More Options" to see conservative/aggressive sizing
4. Click "Optimize with Battery" to run LP optimization
5. See value bridge showing revenue breakdown
6. Move to Stage 3 for investment decision

Author: Aswath
Date: 2025-12-11
"""

import streamlit as st
import plotly.graph_objects as go
from backend.app.services.auto_sizing_service import auto_sizing_service
from backend.app.services.optimization_service import optimization_service
from ui.progress_indicator import render_stage_header
from ui.css import get_tooltip_css
from ui.components import render_metric_card


def render_stage2_inputs(pv_capacity_mw):
    """
    Render battery configuration inputs with smart defaults.
    
    Shows:
    - Smart defaults based on PV capacity
    - "Use Smart Defaults" quick button
    - Manual configuration options
    - Collapsible section for alternative sizing modes
    
    Parameters:
    -----------
    pv_capacity_mw : float
        PV capacity to base smart defaults on
        
    Returns:
    --------
    tuple
        (bess_config dict, optimize_button bool)
    """
    # ===================================================================
    # SMART DEFAULTS DISPLAY
    # ===================================================================
    st.markdown("### Battery Configuration")
    
    # Calculate recommended sizing (moderate mode = 40% of PV)
    smart_defaults = auto_sizing_service.calculate_smart_defaults(
        pv_capacity_mw=pv_capacity_mw,
        mode='moderate'
    )
    
    # Display recommendation
    import textwrap
    info_text = f"""
    **Recommended Battery Sizing** (based on your {pv_capacity_mw} MW PV system):
    
    - **Power**: {smart_defaults['power_mw']} MW ({smart_defaults['power_ratio']:.0%} of PV capacity)
    - **Duration**: {smart_defaults['duration_hours']} hours
    - **Capacity**: {smart_defaults['capacity_mwh']} MWh
    
    {smart_defaults['rationale']}
    """
    # Blue Box (Info/Recommendation) Style
    st.markdown(f"""
    <div style="
        background-color: rgba(59, 130, 246, 0.05); 
        padding: 1rem; 
        border-radius: 8px; 
        border: 1px solid rgba(59, 130, 246, 0.2);
        margin-bottom: 1rem;
    ">
        <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
            <strong>Recommended Battery Sizing</strong> (based on your {pv_capacity_mw} MW PV system):
            <ul style="margin-top: 0.5rem; margin-bottom: 0.5rem; padding-left: 1.5rem;">
                <li><strong>Power</strong>: {smart_defaults['power_mw']} MW ({smart_defaults['power_ratio']:.0%} of PV capacity)</li>
                <li><strong>Duration</strong>: {smart_defaults['duration_hours']} hours</li>
                <li><strong>Capacity</strong>: {smart_defaults['capacity_mwh']} MWh</li>
            </ul>
            <div style="opacity: 0.9; margin-top: 0.5rem;">
                {smart_defaults['rationale']}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===================================================================
    # BATTERY CONFIGURATION
    # ===================================================================
    st.markdown("### 🔋 Battery Configuration")
    
    with st.expander("Configure Battery Parameters", expanded=True):
        # Quick defaults button vs manual configuration
        use_defaults = st.checkbox(
            "Use Smart Defaults (Recommended)",
            value=True,
            help="Use the recommended sizing from above"
        )
        
        if use_defaults:
            # USE SMART DEFAULTS
            bess_power_mw = smart_defaults['power_mw']
            bess_capacity_mwh = smart_defaults['capacity_mwh']
            
            # Show what we're using (read-only display)
            # Use 4 columns to keep cards compact and professional
            col1, col2, col3, col4 = st.columns(4)
            
            # Calculate derived metrics for display
            duration_hours = bess_capacity_mwh / bess_power_mw if bess_power_mw > 0 else 0
            power_ratio = bess_power_mw / pv_capacity_mw if pv_capacity_mw > 0 else 0
            
            with col1:
                st.markdown(render_metric_card("Power", f"{bess_power_mw} MW"), unsafe_allow_html=True)
            with col2:
                st.markdown(render_metric_card("Capacity", f"{bess_capacity_mwh} MWh"), unsafe_allow_html=True)
            with col3:
                st.markdown(render_metric_card("Duration", f"{duration_hours:.1f} hours"), unsafe_allow_html=True)
            with col4:
                st.markdown(render_metric_card("Power Ratio", f"{power_ratio:.0%} of PV"), unsafe_allow_html=True)
                
        else:
            # MANUAL CONFIGURATION
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Battery Power")
                bess_power_mw = st.number_input(
                    "Power Rating (MW)",
                    value=smart_defaults['power_mw'],
                    step=0.5,
                    min_value=0.5,
                    help="How fast the battery can charge/discharge"
                )
            
            with col2:
                st.markdown("#### Battery Capacity")
                bess_capacity_mwh = st.number_input(
                    "Energy Capacity (MWh)",
                    value=smart_defaults['capacity_mwh'],
                    step=1.0,
                    min_value=1.0,
                    help="Total energy storage"
                )
            
            # Calculate and show derived metrics
            duration_hours = bess_capacity_mwh / bess_power_mw if bess_power_mw > 0 else 0
            power_ratio = bess_power_mw / pv_capacity_mw if pv_capacity_mw > 0 else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Duration (Hours at Full Power)",
                    f"{duration_hours:.1f} hours",
                    help="Time battery can discharge at full power = Capacity (MWh) ÷ Power (MW)"
                )
                
                # Add comprehensive explanation
                with st.expander("🤔 What does battery duration mean?"):
                    st.markdown(f"""
                    **Battery Duration** is the time your battery can discharge at **full power** continuously.
                    
                    **For Your Configuration:**
                    - **Capacity**: {bess_capacity_mwh} MWh (total energy stored)
                    - **Power**: {bess_power_mw} MW (max charge/discharge rate)
                    - **Duration**: {duration_hours:.1f} hours = {bess_capacity_mwh} MWh ÷ {bess_power_mw} MW
                    
                    **What this means:**
                    - ✅ Can discharge at {bess_power_mw} MW for {duration_hours:.1f} continuous hours
                    - ✅ Can charge at {bess_power_mw} MW for {duration_hours:.1f} continuous hours
                    - ⚠️ Cannot discharge faster than {bess_power_mw} MW (limited by inverter)
                    
                    **Common Durations by Use Case:**
                    - **1-hour**: Frequency regulation, fast response
                    - **2-hour**: Peaking support, grid services
                    - **4-hour**: Energy arbitrage (recommended for PV+storage)
                    - **6+ hours**: Long-duration storage, seasonal shifting
                    
                    **Example:** A 16 MWh / 4 MW battery (4-hour duration) can:
                    - Charge during low-price hours (e.g., solar midday)
                    - Store energy for 4 hours of full-power discharge
                    - Discharge during evening peak prices
                    """)
            
            with col2:
                st.metric(
                    "Power Ratio",
                    f"{power_ratio:.0%} of PV",
                    help="Battery power as % of PV capacity"
                )
            
            # Validation warnings
            validation = auto_sizing_service.validate_battery_sizing(
                power_mw=bess_power_mw,
                capacity_mwh=bess_capacity_mwh,
                pv_capacity_mw=pv_capacity_mw
            )
            
            if validation['has_warnings']:
                for warning in validation['warnings']:
                    st.warning(warning)
        
        # ===================================================================
        # BATTERY CAPEX
        # ===================================================================
        st.markdown("---")
        st.markdown("#### Battery Economics")
        
        bess_cost_eur_kwh = st.number_input(
            "Battery Cost (€/kWh)",
            value=300.0,
            step=10.0,
            min_value=100.0,
            max_value=500.0,
            help="Fully installed cost including inverter (typical: €250-350/kWh)"
        )
        
        # Show total CAPEX
        total_bess_capex = bess_capacity_mwh * 1000 * bess_cost_eur_kwh
        st.markdown(f'<h4 class="capex-text">Total Battery CAPEX: €{total_bess_capex/1e6:.2f}M</h4>', unsafe_allow_html=True)
    
    # ===================================================================
    # MORE OPTIONS (Collapsible)
    # ===================================================================
    with st.expander("🔧 More Sizing Options (Conservative / Aggressive)"):
        st.caption("Compare different sizing strategies")
        
        # Get all three sizing options
        all_options = auto_sizing_service.get_all_sizing_options(pv_capacity_mw)
        
        # Display as table
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Conservative**")
            st.markdown(f"<div style='min-height: 12rem; font-size: 0.9em; color: gray;'>{all_options['conservative']['rationale']}</div>", unsafe_allow_html=True)
            st.markdown(render_metric_card("Power", f"{all_options['conservative']['power_mw']} MW"), unsafe_allow_html=True)
            st.markdown(render_metric_card("Capacity", f"{all_options['conservative']['capacity_mwh']} MWh"), unsafe_allow_html=True)
            st.markdown(render_metric_card("Duration", f"{all_options['conservative']['duration_hours']}h"), unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Moderate** ⭐")
            st.markdown(f"<div style='min-height: 12rem; font-size: 0.9em; color: gray;'>{all_options['moderate']['rationale']}</div>", unsafe_allow_html=True)
            st.markdown(render_metric_card("Power", f"{all_options['moderate']['power_mw']} MW"), unsafe_allow_html=True)
            st.markdown(render_metric_card("Capacity", f"{all_options['moderate']['capacity_mwh']} MWh"), unsafe_allow_html=True)
            st.markdown(render_metric_card("Duration", f"{all_options['moderate']['duration_hours']}h"), unsafe_allow_html=True)
        
        with col3:
            st.markdown("**Aggressive**")
            st.markdown(f"<div style='min-height: 12rem; font-size: 0.9em; color: gray;'>{all_options['aggressive']['rationale']}</div>", unsafe_allow_html=True)
            st.markdown(render_metric_card("Power", f"{all_options['aggressive']['power_mw']} MW"), unsafe_allow_html=True)
            st.markdown(render_metric_card("Capacity", f"{all_options['aggressive']['capacity_mwh']} MWh"), unsafe_allow_html=True)
            st.markdown(render_metric_card("Duration", f"{all_options['aggressive']['duration_hours']}h"), unsafe_allow_html=True)
    
    # ===================================================================
    # OPTIMIZE BUTTON
    # ===================================================================
    # ===================================================================
    # OPTIMIZE BUTTON
    # ===================================================================
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1]) # Equal columns to center
    with col2:
        optimize_button = st.button(
            "⚡ Optimize with Battery",
            type="primary",
            use_container_width=True,
            help="Run LP optimization to find optimal battery dispatch"
        )
    
    # ===================================================================
    # RETURN CONFIGURATION
    # ===================================================================
    return {
        'power_mw': bess_power_mw,
        'capacity_mwh': bess_capacity_mwh,
        'cost_eur_kwh': bess_cost_eur_kwh
    }, optimize_button


def render_stage2_results(optimization_result, baseline_result, analysis_start_date=None):
    """
    Display optimization results with value bridge and charts.
    
    Parameters:
    -----------
    optimization_result : dict
        Result from optimization_service.run_optimization()
    baseline_result : dict
        Result from baseline_service (for comparison)
    analysis_start_date : pd.Timestamp, optional
        Start date of the analysis period for correct chart indexing
    """
    
    # ===================================================================
    # ===================================================================
    # METRICS HEADER
    # ===================================================================
    
    # ===================================================================
    # KEY METRICS
    # ===================================================================
    st.markdown("### 💰 Revenue Comparison")
    st.markdown(get_tooltip_css(), unsafe_allow_html=True)
    
    baseline_revenue = baseline_result['total_revenue_eur']
    optimized_revenue = optimization_result['financials']['total_revenue_eur']
    incremental_revenue = optimized_revenue - baseline_revenue
    improvement_pct = (incremental_revenue / baseline_revenue * 100) if baseline_revenue > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    
    with col1:
        st.markdown(render_metric_card(
            label="PV Only (Baseline)",
            value=f"€{baseline_revenue:,.0f}",
            help_text="Revenue without battery"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(
            label="PV + Battery",
            value=f"€{optimized_revenue:,.0f}",
            help_text="Revenue with optimized battery"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_metric_card(
            label="Revenue Increase",
            value=f"{improvement_pct:.1f}%",
            delta=f"€{incremental_revenue:,.0f}",
            delta_color="normal",
            help_text="Percentage improvement from adding battery"
        ), unsafe_allow_html=True)
    
    with col4:
        cycles = optimization_result['financials']['annual_cycles']
        st.markdown(render_metric_card(
            label="Battery Cycles",
            value=f"{cycles:.1f}/year",
            help_text="Full discharge cycles per year (affects battery lifetime)"
        ), unsafe_allow_html=True)
    
    # ===================================================================
    # VALUE BRIDGE WATERFALL CHART
    # ===================================================================
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 📊 Value Bridge: Where Does the Revenue Come From?")
    
    st.caption("""
    This waterfall chart breaks down how battery storage increases your revenue.
    Each bar shows a different revenue source.
    """)

    render_value_bridge_waterfall(
        baseline_revenue=baseline_revenue,
        optimized_revenue=optimized_revenue,
        optimization_result=optimization_result,
        baseline_result=baseline_result
    )
    
    # ===================================================================
    # BATTERY UTILIZATION
    # ===================================================================
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 🔋 Battery Performance Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    fin = optimization_result['financials']
    arb = optimization_result['arbitrage']
    
    with col1:
        st.markdown(render_metric_card(
            label="Utilization",
            value=f"{fin['battery_utilization_percent']:.1f}%",
            help_text="% of hours when battery is actively charging or discharging"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(
            label="Avg Charge Price",
            value=f"€{arb['avg_charging_price']:.1f}/MWh",
            help_text="Average price when battery charges"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_metric_card(
            label="Avg Discharge Price",
            value=f"€{arb['avg_discharging_price']:.1f}/MWh",
            delta=f"€{arb['price_spread']:.1f} spread",
            delta_color="normal",
            help_text="Average price when battery discharges"
        ), unsafe_allow_html=True)
    
    # ===================================================================
    # OPERATIONS & SOC CHARTS (With Toggle)
    # ===================================================================
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 📈 Operations Timeline")
    
    # Toggle for Time Range - Controls BOTH charts
    col_toggle, col_spacer = st.columns([1, 3])
    with col_toggle:
        view_mode = st.radio(
            "View Range",
            ["First Week (Hourly)", "Full Year (Monthly Avg)"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    # Process data based on toggle
    import pandas as pd
    
    if view_mode == "First Week (Hourly)":
        # === HOURLY VIEW ===
        # Use the explicit hourly_data (which is truncated to 1 week)
        df = pd.DataFrame(optimization_result['hourly_data'])
        plot_df = df.iloc[:168].copy()
        
        # Power & Price Logic
        x_col = plot_df.index
        y_pv = plot_df['pv_power_kw']
        y_bess = plot_df['bess_flow_kw']
        y_price = plot_df['price_eur_mwh']
        y_soc = plot_df['soc_kwh']
        
        y_unit_power = "kW"
        y_unit_energy = "kWh"
        title_suffix = "(First Week)"
        x_title = "Hour"
        
    else:
        # === MONTHLY VIEW ===
        # Use full year dataframe if available, otherwise fall back to hourly (which will be broken/short)
        if 'full_year_df' in optimization_result:
            df = optimization_result['full_year_df'].copy()
        else:
            df = pd.DataFrame(optimization_result['hourly_data'])

        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            # Use provided start date or fallback
            if 'analysis_start_date' in locals() and analysis_start_date is not None:
                start_date = analysis_start_date
            else:
                start_date = pd.Timestamp.now().normalize() - pd.DateOffset(years=1)
                
            df.index = pd.date_range(start=start_date, periods=len(df), freq='h')
            
        # Resample - Power/Price = Mean, SOC = Mean (smoother) or Last (end of month)
        # Using Mean for SOC gives a better idea of "average fullness"
        resampled = df.resample('ME').mean() # Use 'ME' for Month End (pandas 2.0+) or 'M'
        
        plot_df = resampled
        x_col = plot_df.index.strftime('%b')
        
        # Convert units for annual view
        y_pv = plot_df['pv_power_kw'] / 1000 # MW
        y_bess = plot_df['bess_flow_kw'] / 1000 # MW
        y_price = plot_df['price_eur_mwh'] 
        y_soc = plot_df['soc_kwh'] / 1000 # MWh
        
        y_unit_power = "MW (Avg)"
        y_unit_energy = "MWh (Avg)"
        title_suffix = "(Annual Average)"
        x_title = "Month"

    # Render Charts
    render_operations_chart_v2(x_col, y_pv, y_bess, y_price, y_unit_power, title_suffix, x_title)
    
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 🔋 Battery State of Charge")
    
    render_soc_chart_v2(x_col, y_soc, y_unit_energy, title_suffix, x_title)


def render_value_bridge_waterfall(baseline_revenue, optimized_revenue, optimization_result, baseline_result):
    """
    Create waterfall chart showing revenue breakdown.
    
    Shows:
    - Base PV Revenue (from baseline)
    - + Arbitrage Gain (from price spread trading)
    - + Negative Price Savings (avoiding losses)
    - + Curtailment Recovery (not shown separately due to data complexity)
    - = Total Revenue with BESS
    """
    
    # Calculate components
    arbitrage_revenue = optimization_result['arbitrage']['estimated_arbitrage_revenue']
    negative_price_savings = optimization_result['negative_prices']['estimated_savings']
    
    # Other revenue sources (residual)
    total_incremental = optimized_revenue - baseline_revenue
    other_revenue = total_incremental - arbitrage_revenue - negative_price_savings
    other_revenue = max(0, other_revenue)  # Ensure non-negative
    
    # Create waterfall chart
    fig = go.Figure(go.Waterfall(
        name="Revenue",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=[
            "PV Baseline<br>(No Battery)",
            "Arbitrage<br>Revenue",
            "Negative Price<br>Avoidance",
            "Other<br>Benefits",
            "Total with<br>Battery"
        ],
        y=[
            baseline_revenue,
            arbitrage_revenue,
            negative_price_savings,
            other_revenue,
            optimized_revenue
        ],
        text=[
            f"€{baseline_revenue/1e6:.2f}M",
            f"+€{arbitrage_revenue/1e3:.0f}k",
            f"+€{negative_price_savings/1e3:.0f}k",
            f"+€{other_revenue/1e3:.0f}k",
            f"€{optimized_revenue/1e6:.2f}M"
        ],
        textposition="outside",
        textfont=dict(size=12),
        connector={"line": {"color": "rgb(63, 63, 63)", "width": 2}},
        increasing={"marker": {"color": "#10b981"}},  # Green for gains
        decreasing={"marker": {"color": "#ef4444"}},  # Red (shouldn't have any)
        totals={"marker": {"color": "#3b82f6"}}  # Blue for totals
    ))
    
    fig.update_layout(
        title="Revenue Value Bridge: PV Only → PV + Battery",
        showlegend=False,
        height=450,
        yaxis_title="Annual Revenue (€)",
        margin=dict(l=20, r=20, t=60, b=40), # Reduced bottom margin
        annotations=[dict(
            text="Waterfall chart showing incremental revenue sources from battery storage.",
            x=0.5, y=0.02, # Moved inside (bottom)
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=12, color="gray"),
            yanchor="bottom"
        )]
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_operations_chart_v2(x, y_pv, y_bess, y_price, unit, suffix, x_title):
    fig = go.Figure()
    
    # PV Generation
    fig.add_trace(go.Scatter(
        x=x, y=y_pv, name="PV Generation",
        fill='tozeroy', line=dict(color='#f59e0b', width=1), opacity=0.6,
        hovertemplate=f"%{{y:.1f}} {unit}"
    ))
    
    # Battery Flow
    fig.add_trace(go.Bar(
        x=x, y=y_bess, name="Battery Flow",
        marker_color='#3b82f6',
        hovertemplate=f"%{{y:.1f}} {unit}"
    ))
    
    # Price
    fig.add_trace(go.Scatter(
        x=x, y=y_price, name="Market Price",
        line=dict(color='#ef4444', width=2), yaxis='y2',
        hovertemplate="%{y:.1f} €/MWh"
    ))
    
    fig.update_layout(
        # title=f"Power Flow and Prices {suffix}", # Remove title inside graph for polish
        xaxis_title=x_title,
        yaxis_title=f"Power ({unit})",
        yaxis2=dict(title="Price (€/MWh)", overlaying='y', side='right'),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        height=400,
        margin=dict(l=20, r=20, t=20, b=20), # Tight margin
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_soc_chart_v2(x, y_soc, unit, suffix, x_title):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x, y=y_soc, name="State of Charge",
        fill='tozeroy', line=dict(color='#10b981', width=2),
        hovertemplate=f"%{{y:.1f}} {unit}"
    ))
    
    fig.update_layout(
        # title=f"Battery SoC {suffix}",
        xaxis_title=x_title,
        yaxis_title=f"Energy ({unit})",
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# Legacy function stubs to prevent errors if called, but not used
def render_operations_chart(r): pass
def render_soc_chart(r): pass
