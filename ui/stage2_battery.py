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
    st.info(f"""
    **Recommended Battery Sizing** (based on your {pv_capacity_mw} MW PV system):
    
    - **Power**: {smart_defaults['power_mw']} MW ({smart_defaults['power_ratio']:.0%} of PV capacity)
    - **Duration**: {smart_defaults['duration_hours']} hours
    - **Capacity**: {smart_defaults['capacity_mwh']} MWh
    
    {smart_defaults['rationale']}
    """)
    
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
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Power", f"{bess_power_mw} MW")
            with col2:
                st.metric("Capacity", f"{bess_capacity_mwh} MWh")
                
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
        st.caption(f"**Total Battery CAPEX:** €{total_bess_capex/1e6:.2f}M")
    
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
            st.caption(all_options['conservative']['rationale'])
            st.metric("Power", f"{all_options['conservative']['power_mw']} MW")
            st.metric("Capacity", f"{all_options['conservative']['capacity_mwh']} MWh")
            st.metric("Duration", f"{all_options['conservative']['duration_hours']}h")
        
        with col2:
            st.markdown("**Moderate** ⭐")
            st.caption("Recommended (current)")
            st.metric("Power", f"{all_options['moderate']['power_mw']} MW")
            st.metric("Capacity", f"{all_options['moderate']['capacity_mwh']} MWh")
            st.metric("Duration", f"{all_options['moderate']['duration_hours']}h")
        
        with col3:
            st.markdown("**Aggressive**")
            st.caption(all_options['aggressive']['rationale'])
            st.metric("Power", f"{all_options['aggressive']['power_mw']} MW")
            st.metric("Capacity", f"{all_options['aggressive']['capacity_mwh']} MWh")
            st.metric("Duration", f"{all_options['aggressive']['duration_hours']}h")
    
    # ===================================================================
    # OPTIMIZE BUTTON
    # ===================================================================
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
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


def render_stage2_results(optimization_result, baseline_result):
    """
    Display optimization results with value bridge and charts.
    
    Parameters:
    -----------
    optimization_result : dict
        Result from optimization_service.run_optimization()
    baseline_result : dict
        Result from baseline_service (for comparison)
    """
    
    # ===================================================================
    # SUCCESS MESSAGE
    # ===================================================================
    st.success("✅ Optimization Complete!")
    
    # ===================================================================
    # KEY METRICS
    # ===================================================================
    st.markdown("### 💰 Revenue Comparison")
    
    baseline_revenue = baseline_result['total_revenue_eur']
    optimized_revenue = optimization_result['financials']['total_revenue_eur']
    incremental_revenue = optimized_revenue - baseline_revenue
    improvement_pct = (incremental_revenue / baseline_revenue * 100) if baseline_revenue > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "PV Only (Baseline)",
            f"€{baseline_revenue:,.0f}",
            help="Revenue without battery"
        )
    
    with col2:
        st.metric(
            "PV + Battery",
            f"€{optimized_revenue:,.0f}",
            delta=f"+€{incremental_revenue:,.0f}",
            delta_color="normal",
            help="Revenue with optimized battery"
        )
    
    with col3:
        st.metric(
            "Revenue Increase",
            f"{improvement_pct:.1f}%",
            delta=f"+€{incremental_revenue:,.0f}/year",
            delta_color="normal",
            help="Percentage improvement from adding battery"
        )
    
    with col4:
        cycles = optimization_result['financials']['annual_cycles']
        st.metric(
            "Battery Cycles",
            f"{cycles:.1f}/year",
            help="Full discharge cycles per year (affects battery lifetime)"
        )
    
    # ===================================================================
    # VALUE BRIDGE WATERFALL CHART
    # ===================================================================
    st.markdown("---")
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
    st.markdown("---")
    st.markdown("### 🔋 Battery Performance Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    fin = optimization_result['financials']
    arb = optimization_result['arbitrage']
    
    with col1:
        st.metric(
            "Utilization",
            f"{fin['battery_utilization_percent']:.1f}%",
            help="% of hours when battery is actively charging or discharging"
        )
    
    with col2:
        st.metric(
            "Avg Charge Price",
            f"€{arb['avg_charging_price']:.1f}/MWh",
            help="Average price when battery charges"
        )
    
    with col3:
        st.metric(
            "Avg Discharge Price",
            f"€{arb['avg_discharging_price']:.1f}/MWh",
            delta=f"+€{arb['price_spread']:.1f} spread",
            delta_color="normal",
            help="Average price when battery discharges"
        )
    
    # ===================================================================
    # OPERATIONS CHARTS
    # ===================================================================
    st.markdown("---")
    st.markdown("### 📈 Operations Timeline (First Week)")
    
    render_operations_chart(optimization_result)
    
    # ===================================================================
    # BATTERY STATE OF CHARGE
    # ===================================================================
    st.markdown("### 🔋 Battery State of Charge")
    
    render_soc_chart(optimization_result)


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
        margin=dict(l=20, r=20, t=60, b=80)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_operations_chart(optimization_result):
    """
    Chart showing PV generation, battery flow, and prices over time.
    """
    import pandas as pd
    
    df = pd.DataFrame(optimization_result['hourly_data'])
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # PV Generation (area)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['pv_power_kw'],
        name="PV Generation",
        fill='tozeroy',
        line=dict(color='#f59e0b', width=1),
        opacity=0.6
    ))
    
    # Battery Flow (bar)
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['bess_flow_kw'],
        name="Battery Flow",
        marker_color='#3b82f6'
    ))
    
    # Price (line on secondary axis)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['price_eur_mwh'],
        name="Market Price",
        line=dict(color='#ef4444', width=2),
        yaxis='y2'
    ))
    
    # Layout
    fig.update_layout(
        title="Power Flow and Prices (First Week)",
        xaxis_title="Hour",
        yaxis_title="Power (kW)",
        yaxis2=dict(
            title="Price (€/MWh)",
            overlaying='y',
            side='right'
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450,
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_soc_chart(optimization_result):
    """
    Chart showing battery state of charge over time.
    """
    import pandas as pd
    
    df = pd.DataFrame(optimization_result['hourly_data'])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['soc_kwh'],
        name="State of Charge",
        fill='tozeroy',
        line=dict(color='#10b981', width=2)
    ))
    
    fig.update_layout(
        title="Battery State of Charge Over Time",
        xaxis_title="Hour",
        yaxis_title="Energy Stored (kWh)",
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
