"""
Stage 3: Investment Analysis Component
=======================================

This component implements the financial analysis stage of the user journey.
It provides rigorous financial metrics including IRR, NPV, and payback period,
with interactive sensitivity analysis capabilities.

Purpose:
--------
Provide investors with comprehensive financial metrics for informed decision-making.
The interactive sensitivity analysis enables scenario exploration without
re-executing the optimization.

Key Outputs:
------------
1. IRR (Internal Rate of Return) for greenfield and brownfield scenarios
2. NPV (Net Present Value) at user-defined discount rate
3. Payback Period (simple and discounted)
4. Interactive sensitivity analysis
5. IRR sensitivity curves (vs CAPEX, vs Duration)

User Flow:
----------
1. Review scenario configuration (Greenfield or Brownfield)
2. Adjust project parameters (lifetime, discount rate)
3. Review financial metrics
4. Utilize sensitivity analysis for scenario exploration
5. Configure advanced parameters (degradation rates)
6. Evaluate investment decision

Author: Aswath
Date: 2025-12-11
"""

import streamlit as st
import plotly.graph_objects as go
import html
from backend.app.services.financial_service import financial_service
from ui.progress_indicator import render_stage_header
from ui.css import get_tooltip_css
from ui.components import render_metric_card
import numpy as np


def render_stage3(
    optimization_result,
    baseline_result,
    pv_config,
    bess_config
):
    """
    Render complete Stage 3: Investment Decision.
    
    Parameters:
    -----------
    optimization_result : dict
        Optimization results from Stage 2
    baseline_result : dict
        Baseline results from Stage 1
    pv_config : dict
        PV configuration
    bess_config : dict
        Battery configuration
    """
    
    # ===================================================================
    # STAGE HEADER
    # ===================================================================
    st.markdown("### Financial Feasibility Analysis")
    st.markdown(get_tooltip_css(), unsafe_allow_html=True)
    
    # ===================================================================
    # PROJECT SCENARIO DISPLAY
    # ===================================================================
    # Use configuration from Stage 1 instead of asking again
    scenario = pv_config.get('project_type', 'Greenfield')
    
    st.caption(f"Scenario: **{scenario}**")
    
    # Explain the selected scenario
    if scenario == "Greenfield":
        st.markdown("""
        <div style="
            background-color: rgba(59, 130, 246, 0.05); 
            padding: 1rem; 
            border-radius: 8px; 
            border: 1px solid rgba(59, 130, 246, 0.2);
            margin-bottom: 1rem;
        ">
            <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
                <strong>Greenfield Project (Integrated Asset)</strong>
                <ul style="margin-top: 0.5rem; margin-bottom: 0px; padding-left: 1.5rem;">
                    <li>Evaluation of combined Solar + Storage asset from inception.</li>
                    <li>IRR reflects total capital deployment efficiency.</li>
                    <li>Full revenue stack (Energy + Arbitrage) considered against total CAPEX.</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background-color: rgba(59, 130, 246, 0.05); 
            padding: 1rem; 
            border-radius: 8px; 
            border: 1px solid rgba(59, 130, 246, 0.2);
            margin-bottom: 1rem;
        ">
            <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
                <strong>Brownfield Project (Retrofit)</strong>
                <ul style="margin-top: 0.5rem; margin-bottom: 0px; padding-left: 1.5rem;">
                    <li>Evaluation of BESS addition to an operational Solar asset.</li>
                    <li>IRR reflects strict marginal return on storage CAPEX.</li>
                    <li> Revenue = Incremental arbitrage/capacity uplift only.</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ===================================================================
    # PROJECT PARAMETERS
    # ===================================================================
    st.markdown("---")
    st.markdown("### ⚙️ Financial Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Project Lifetime
        # User-specified: 10-30 years, default 20
        project_lifetime = st.slider(
            "Project Lifetime (years)",
            min_value=10,
            max_value=30,
            value=25,  # Default
            step=1,
            help="Expected operational horizon for Cash Flow analysis"
        )
    
    with col2:
        # Discount Rate
        # User-specified: 4-20%, default 8%
        discount_rate = st.slider(
            "WACC / Discount Rate (%)",
            min_value=4.0,
            max_value=15.0,
            value=7.0,  # Default
            step=0.5,
            help="Weighted Average Cost of Capital - Hurdle rate for NPV"
        )
    
    # ===================================================================
    # ADVANCED SETTINGS (Degradation Rates)
    # ===================================================================
    with st.expander("🔧 Technical Assumptions (Degradation)"):
        st.caption("Asset performance degradation vectors.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # PV Degradation
            # User-specified: default 1%/year
            pv_degradation = st.number_input(
                "PV Degradation Rate (%/year)",
                value=0.5,
                step=0.1,
                min_value=0.0,
                max_value=3.0,
                help="Annual yield reduction factor"
            ) / 100  # Convert to decimal
        
        with col2:
            # Battery Degradation
            # User-specified: default 2%/year
            battery_degradation = st.number_input(
                "SoH Degradation Rate (%/year)",
                value=2.0,
                step=0.1,
                min_value=0.0,
                max_value=5.0,
                help="State of Health reduction (affecting capacity)"
            ) / 100  # Convert to decimal
    
    # ===================================================================
    # CALCULATE BASE FINANCIAL METRICS
    # ===================================================================
    # Get annual revenues
    optimized_revenue = optimization_result['financials']['total_revenue_eur']
    baseline_revenue = baseline_result['total_revenue_eur']
    
    # Calculate IRR
    irr_result = financial_service.calculate_irr(
        scenario=scenario.lower(),
        annual_revenue_eur=optimized_revenue,
        pv_config=pv_config,
        bess_config=bess_config,
        project_lifetime_years=project_lifetime,
        pv_degradation_rate=pv_degradation,
        battery_degradation_rate=battery_degradation,
        baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None,
        discount_rate=discount_rate / 100.0  # Pass the slider value!
    )
    
    # Store in session state for sensitivity analysis
    st.session_state.base_irr_result = irr_result
    
    # ===================================================================
    # DISPLAY FINANCIAL METRICS
    # ===================================================================
    st.markdown("---")
    st.markdown("### Key Performance Indicators")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # IRR
        irr_pct = irr_result['irr_percent']
        
        # Color code based on IRR
        if irr_pct and irr_pct > 10:
            irr_status = "Robust"
            irr_color = "normal"
        elif irr_pct and irr_pct > 6:
            irr_status = "Moderate"
            irr_color = "off"
        else:
            irr_status = "Marginal"
            irr_color = "inverse"
        
        st.markdown(render_metric_card(
            label="Project IRR",
            value=f"{irr_pct:.1f}%" if irr_pct else "N/A",
            delta=irr_status,
            delta_color=irr_color,
            help_text="Internal Rate of Return (Unlevered)"
        ), unsafe_allow_html=True)
    
    with col2:
        # NPV
        npv_eur = irr_result['npv_eur']
        npv_millions = npv_eur / 1e6
        
        st.markdown(render_metric_card(
            label=f"NPV @ {discount_rate:.1f}%",
            value=f"€{npv_millions:.2f}M",
            delta="Value Accretive" if npv_eur > 0 else "Value Dilutive",
            delta_color="normal" if npv_eur > 0 else "inverse",
            help_text="Net Present Value of future cash flows"
        ), unsafe_allow_html=True)
    
    with col3:
        # Payback Period
        payback = irr_result['payback_period_simple_years']
        
        st.markdown(render_metric_card(
            label="Payback Period",
            value=f"{payback:.1f} years" if payback else "N/A",
            help_text="Simple capital recovery period"
        ), unsafe_allow_html=True)
    
    # Show investment breakdown in a clean info box
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="
        background-color: rgba(59, 130, 246, 0.05);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(59, 130, 246, 0.2);
        margin-bottom: 1rem;
    ">
        <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
            <strong>Capital Structure</strong>
            <ul style="margin-top: 0.5rem; margin-bottom: 0px; padding-left: 1.5rem;">
                <li><strong>Total CAPEX Requirement:</strong> {html.escape(str(irr_result['capex_description']))}</li>
                <li><strong>Year 1 Recurring Revenue:</strong> €{irr_result['first_year_revenue_eur']:,.0f}</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===================================================================
    # REAL-TIME SENSITIVITY ANALYSIS
    # ===================================================================
    st.markdown("---")
    st.markdown("### Sensitivity Analysis")

    st.caption("""
    Evaluate the sensitivity of project returns to variations in capital expenditure and system sizing parameters.
    The charts below illustrate the response curves for your current configuration.
    """)
    
    # Create two columns for sensitivity sliders
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Battery CAPEX Sensitivity")
        
        # CAPEX sensitivity slider
        # Range: €200-400/kWh, default is current value
        current_capex = bess_config['cost_eur_kwh']
        capex_sensitivity = st.slider(
            "Battery Cost (€/kWh)",
            min_value=150.0,
            max_value=450.0,
            value=current_capex,
            step=10.0,
            key="capex_slider",
            help="Adjust battery cost assumption"
        )
        
        # Show change from base
        capex_delta = capex_sensitivity - current_capex
        if capex_delta != 0:
            st.caption(f"Delta: {capex_delta:+.0f} €/kWh")
    
    with col2:
        st.markdown("#### Duration Scaling Sensitivity")
        
        # Duration sensitivity slider
        # Range: 2-6 hours
        base_duration = bess_config['capacity_mwh'] / bess_config['power_mw']
        
        duration_sensitivity = st.slider(
            "Duration (hours)",
            min_value=1.0,
            max_value=8.0,
            value=base_duration,
            step=0.5,
            key="duration_slider",
            help="Adjust storage duration (Capacity/Power ratio)"
        )
        
        # Show change from base
        duration_delta = duration_sensitivity - base_duration
        if duration_delta != 0:
            st.caption(f"Delta: {duration_delta:+.1f} hours")
    
    # ===================================================================
    # CALCULATE ADJUSTED IRR
    # ===================================================================
    # Only recalculate if parameters changed
    
    # Always calculate "current" state based on slider values for the "Current" dot/line
    adjusted_bess_config = bess_config.copy()
    adjusted_bess_config['cost_eur_kwh'] = capex_sensitivity
    adjusted_bess_config['capacity_mwh'] = bess_config['power_mw'] * duration_sensitivity
    
    adjusted_irr_result = financial_service.calculate_irr(
        scenario=scenario.lower(),
        annual_revenue_eur=optimized_revenue,  # Same revenue (simplification)
        pv_config=pv_config,
        bess_config=adjusted_bess_config,
        project_lifetime_years=project_lifetime,
        pv_degradation_rate=pv_degradation,
        battery_degradation_rate=battery_degradation,
        baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None
    )
    
    adjusted_irr = adjusted_irr_result['irr_percent']
    irr_change = adjusted_irr - irr_pct if (adjusted_irr and irr_pct) else 0

    if (capex_sensitivity != current_capex or abs(duration_sensitivity - base_duration) > 0.01):
        st.markdown("#### Adjusted Scenario Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(render_metric_card(
                label="Scenario IRR",
                value=f"{adjusted_irr:.1f}%" if adjusted_irr else "N/A",
                delta=f"{irr_change:+.1f}%",
                delta_color="normal" if irr_change >= 0 else "inverse"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(render_metric_card(
                label="Scenario NPV",
                value=f"€{adjusted_irr_result['npv_eur']/1e6:.2f}M"
            ), unsafe_allow_html=True)
        
        with col3:
            # Show new CAPEX
            st.markdown(render_metric_card(
                label="Scenario CAPEX",
                value=f"€{adjusted_irr_result['capex_bess_eur']/1e6:.2f}M"
            ), unsafe_allow_html=True)
    
    # ===================================================================
    # SENSITIVITY CHARTS
    # ===================================================================
    st.markdown("---")
    st.markdown("### IRR Sensitivity Curves")
    
    render_sensitivity_charts(
        base_irr_result=irr_result, # The original result (reference)
        current_irr_result=adjusted_irr_result, # The dynamic result
        pv_config=pv_config,
        bess_config=bess_config, # Original config
        current_capex=capex_sensitivity,      # Slider value
        current_duration=duration_sensitivity, # Slider value
        scenario=scenario,
        optimized_revenue=optimized_revenue,
        baseline_revenue=baseline_revenue,
        project_lifetime=project_lifetime,
        pv_degradation=pv_degradation,
        battery_degradation=battery_degradation,
        discount_rate=discount_rate / 100.0
    )


def render_sensitivity_charts(
    base_irr_result,
    current_irr_result,
    pv_config,
    bess_config,
    current_capex,
    current_duration,
    scenario,
    optimized_revenue,
    baseline_revenue,
    project_lifetime,
    pv_degradation,
    battery_degradation,
    discount_rate
):
    """
    Render IRR sensitivity charts with dynamic comparison lines.
    
    Line 1 (Dashed): Base Scenario (fixed at initial inputs)
    Line 2 (Solid): Current Scenario (reacts to the OTHER slider)
    """
    
    col1, col2 = st.columns(2)
    
    # Base/Reference Values from initial config
    base_capex = bess_config['cost_eur_kwh']
    base_duration = bess_config['capacity_mwh'] / bess_config['power_mw']
    
    # ===================================================================
    # CHART 1: IRR vs CAPEX (Sensitivity to Cost)
    # Line 1: @ Base Duration
    # Line 2: @ Slider Duration
    # ===================================================================
    with col1:
        st.markdown("#### IRR Response to Battery CAPEX Variation")
        
        vals_x = np.linspace(150, 450, 20)
        
        # Trace 1: Base Duration Curve (Reference)
        y_base = []
        for c in vals_x:
            # Config: Variable Capex, FIXED Base Duration
            cfg = bess_config.copy()
            cfg['cost_eur_kwh'] = c
            # Capacity fixed at base duration
            cfg['capacity_mwh'] = bess_config['power_mw'] * base_duration 
            
            res = financial_service.calculate_irr(
                scenario=scenario.lower(), annual_revenue_eur=optimized_revenue, pv_config=pv_config, bess_config=cfg,
                project_lifetime_years=project_lifetime, pv_degradation_rate=pv_degradation, battery_degradation_rate=battery_degradation,
                baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None,
                discount_rate=discount_rate
            )
            y_base.append(res['irr_percent'] or 0)

        # Trace 2: Current Duration Curve (Dynamic)
        y_curr = []
        for c in vals_x:
            # Config: Variable Capex, FIXED Current Slider Duration
            cfg = bess_config.copy()
            cfg['cost_eur_kwh'] = c
            # Capacity based on SLIDER duration
            cfg['capacity_mwh'] = bess_config['power_mw'] * current_duration
            
            res = financial_service.calculate_irr(
                scenario=scenario.lower(), annual_revenue_eur=optimized_revenue, pv_config=pv_config, bess_config=cfg,
                project_lifetime_years=project_lifetime, pv_degradation_rate=pv_degradation, battery_degradation_rate=battery_degradation,
                baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None,
                discount_rate=discount_rate
            )
            y_curr.append(res['irr_percent'] or 0)
        
        fig1 = go.Figure()
        
        # Plot Reference Line
        fig1.add_trace(go.Scatter(
            x=vals_x, y=y_base, mode='lines', name=f'Base ({base_duration:.1f}h)',
            line=dict(color='gray', width=2, dash='dash')
        ))
        
        # Plot Dynamic Line
        fig1.add_trace(go.Scatter(
            x=vals_x, y=y_curr, mode='lines', name=f'Current ({current_duration:.1f}h)',
            line=dict(color='#3b82f6', width=3)
        ))
        
        # Current configuration marker
        fig1.add_trace(go.Scatter(
            x=[current_capex], y=[current_irr_result['irr_percent']],
            mode='markers', name='Current Configuration',
            marker=dict(size=12, color='#ef4444', line=dict(width=2, color='white'))
        ))
        
        fig1.update_layout(
            xaxis_title="Battery CAPEX (€/kWh)", yaxis_title="IRR (%)",
            height=350, margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    # ===================================================================
    # CHART 2: IRR vs Duration (Sensitivity to Sizing)
    # Line 1: @ Base CAPEX
    # Line 2: @ Slider CAPEX
    # ===================================================================
    with col2:
        st.markdown("#### IRR Response to Duration Variation")
        
        vals_x = np.linspace(1, 8, 20)
        
        # Trace 1: Base CAPEX Curve
        y_base = []
        for d in vals_x:
            # Config: Variable Duration, FIXED Base Capex
            cfg = bess_config.copy()
            cfg['cost_eur_kwh'] = base_capex # Fixed base
            cfg['capacity_mwh'] = bess_config['power_mw'] * d
            
            res = financial_service.calculate_irr(
                scenario=scenario.lower(), annual_revenue_eur=optimized_revenue, pv_config=pv_config, bess_config=cfg,
                project_lifetime_years=project_lifetime, pv_degradation_rate=pv_degradation, battery_degradation_rate=battery_degradation,
                baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None,
                discount_rate=discount_rate
            )
            y_base.append(res['irr_percent'] or 0)
            
        # Trace 2: Current CAPEX Curve
        y_curr = []
        for d in vals_x:
            # Config: Variable Duration, FIXED Slider Capex
            cfg = bess_config.copy()
            cfg['cost_eur_kwh'] = current_capex # From slider
            cfg['capacity_mwh'] = bess_config['power_mw'] * d
            
            res = financial_service.calculate_irr(
                scenario=scenario.lower(), annual_revenue_eur=optimized_revenue, pv_config=pv_config, bess_config=cfg,
                project_lifetime_years=project_lifetime, pv_degradation_rate=pv_degradation, battery_degradation_rate=battery_degradation,
                baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None,
                discount_rate=discount_rate
            )
            y_curr.append(res['irr_percent'] or 0)
            
        fig2 = go.Figure()
        
        # Plot Reference Line
        fig2.add_trace(go.Scatter(
            x=vals_x, y=y_base, mode='lines', name=f'Base (€{base_capex:.0f})',
            line=dict(color='gray', width=2, dash='dash')
        ))
        
        # Plot Dynamic Line
        fig2.add_trace(go.Scatter(
            x=vals_x, y=y_curr, mode='lines', name=f'Current (€{current_capex:.0f})',
            line=dict(color='#10b981', width=3)
        ))
        
        # Current configuration marker
        fig2.add_trace(go.Scatter(
            x=[current_duration], y=[current_irr_result['irr_percent']],
            mode='markers', name='Current Configuration',
            marker=dict(size=12, color='#ef4444', line=dict(width=2, color='white'))
        ))
        
        fig2.update_layout(
            xaxis_title="Duration (Hours)", yaxis_title="IRR (%)",
            height=350, margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig2, use_container_width=True)
