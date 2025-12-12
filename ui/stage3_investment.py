"""
Stage 3: Investment Decision Component
=======================================

This component implements "The Decision" stage of the user journey.
It provides financial rigor with IRR, NPV, and payback period calculations,
plus real-time sensitivity analysis.

Purpose:
--------
Give investors the financial metrics they need to make an informed decision.
The real-time sensitivity sliders allow exploration of "what-if" scenarios
without re-running the optimization.

Key Outputs:
------------
1. IRR (Internal Rate of Return) for greenfield and brownfield scenarios
2. NPV (Net Present Value) at user-defined discount rate
3. Payback Period (simple and discounted)
4. Real-time sensitivity analysis with sliders
5. IRR sensitivity charts (vs CAPEX, vs Duration)

User Flow:
----------
1. Select scenario (Greenfield or Brownfield)
2. Set project parameters (lifetime, discount rate)
3. View financial metrics
4. Adjust sensitivity sliders to see real-time IRR changes
5. Explore advanced settings (degradation rates)
6. Make investment decision

Author: Aswath
Date: 2025-12-11
"""

import streamlit as st
import plotly.graph_objects as go
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
    # ===================================================================
    # STAGE HEADER
    # ===================================================================
    # No icon, standard header style as requested
    st.markdown("### Investment Decision")
    st.markdown(get_tooltip_css(), unsafe_allow_html=True)
    
    # ===================================================================
    # PROJECT SCENARIO DISPLAY
    # ===================================================================
    # Use configuration from Stage 1 instead of asking again
    scenario = pv_config.get('project_type', 'Greenfield')
    
    st.caption(f"Scenario: **{scenario}**")
    
    # Explain the selected scenario
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
                <strong>Greenfield Project</strong>
                <ul style="margin-top: 0.5rem; margin-bottom: 0px; padding-left: 1.5rem;">
                    <li>New solar + battery installation</li>
                    <li>IRR calculated on total investment (PV + BESS)</li>
                    <li>Revenue = Full PV + BESS revenue</li>
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
                <strong>Brownfield Project</strong>
                <ul style="margin-top: 0.5rem; margin-bottom: 0px; padding-left: 1.5rem;">
                    <li>Adding battery to existing solar park</li>
                    <li>IRR calculated on BESS investment only</li>
                    <li>Revenue = Incremental revenue from adding BESS</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ===================================================================
    # PROJECT PARAMETERS
    # ===================================================================
    st.markdown("---")
    st.markdown("### ⚙️ Project Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Project Lifetime
        # User-specified: 10-30 years, default 20
        project_lifetime = st.slider(
            "Project Lifetime (years)",
            min_value=10,
            max_value=30,
            value=20,  # Default
            step=1,
            help="Expected operational lifetime of the project"
        )
    
    with col2:
        # Discount Rate
        # User-specified: 4-20%, default 8%
        discount_rate = st.slider(
            "Discount Rate (%)",
            min_value=4.0,
            max_value=20.0,
            value=8.0,  # Default
            step=0.5,
            help="Required rate of return / cost of capital (WACC)"
        )
    
    # ===================================================================
    # ADVANCED SETTINGS (Degradation Rates)
    # ===================================================================
    with st.expander("🔧 Advanced Settings (Degradation Rates)"):
        st.caption("System performance degrades over time. Adjust these rates if you have specific data.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # PV Degradation
            # User-specified: default 1%/year
            pv_degradation = st.number_input(
                "PV Degradation Rate (%/year)",
                value=1.0,
                step=0.1,
                min_value=0.0,
                max_value=3.0,
                help="Typical: 0.5-1.0% per year for crystalline silicon"
            ) / 100  # Convert to decimal
        
        with col2:
            # Battery Degradation
            # User-specified: default 2%/year
            battery_degradation = st.number_input(
                "Battery Degradation Rate (%/year)",
                value=2.0,
                step=0.1,
                min_value=0.0,
                max_value=5.0,
                help="Typical: 1.5-2.5% per year for Li-ion batteries"
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
        baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None
    )
    
    # Store in session state for sensitivity analysis
    if 'base_irr_result' not in st.session_state:
        st.session_state.base_irr_result = irr_result
    else:
        st.session_state.base_irr_result = irr_result
    
    # ===================================================================
    # DISPLAY FINANCIAL METRICS
    # ===================================================================
    st.markdown("---")
    st.markdown("### 💼 Financial Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # IRR
        irr_pct = irr_result['irr_percent']
        
        # Color code based on IRR
        if irr_pct and irr_pct > 12:
            irr_status = "Excellent"
            irr_color = "normal"
        elif irr_pct and irr_pct > 8:
            irr_status = "Good"
            irr_color = "normal"
        else:
            irr_status = "Review Required"
            irr_color = "inverse"
        
        st.markdown(render_metric_card(
            label="Project IRR",
            value=f"{irr_pct:.1f}%" if irr_pct else "N/A",
            delta=irr_status,
            delta_color=irr_color,
            help_text="Internal Rate of Return - the 'true' annual return on investment"
        ), unsafe_allow_html=True)
    
    with col2:
        # NPV
        npv_eur = irr_result['npv_eur']
        npv_millions = npv_eur / 1e6
        
        st.markdown(render_metric_card(
            label=f"NPV @ {discount_rate:.0f}%",
            value=f"€{npv_millions:.2f}M",
            delta="Positive" if npv_eur > 0 else "Negative",
            delta_color="normal" if npv_eur > 0 else "inverse",
            help_text="Net Present Value - total value in today's money"
        ), unsafe_allow_html=True)
    
    with col3:
        # Payback Period
        payback = irr_result['payback_period_simple_years']
        
        st.markdown(render_metric_card(
            label="Payback Period",
            value=f"{payback:.1f} years" if payback else "N/A",
            help_text="Simple payback - years to recover initial investment"
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
            <strong>💰 Investment Summary</strong>
            <ul style="margin-top: 0.5rem; margin-bottom: 0px; padding-left: 1.5rem;">
                <li><strong>Initial Investment:</strong> {irr_result['capex_description']}</li>
                <li><strong>1st Year Revenue:</strong> €{irr_result['first_year_revenue_eur']:,.0f}</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===================================================================
    # INTERPRETATION GUIDE
    # ===================================================================
    if irr_pct:
        if irr_pct > 12:
            st.markdown(f"""
            <div style="
                background-color: rgba(16, 185, 129, 0.05); 
                padding: 1rem; 
                border-radius: 8px; 
                border: 1px solid rgba(16, 185, 129, 0.2);
                margin-bottom: 1rem;
            ">
                <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
                    <strong style="color: #059669;">✅ Strong Investment Case</strong><br>
                    Your IRR of {irr_pct:.1f}% significantly exceeds typical cost of capital 
                    (~8%) and is excellent for a utility-scale renewable energy project.
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif irr_pct > 8:
            st.markdown(f"""
            <div style="
                background-color: rgba(59, 130, 246, 0.05); 
                padding: 1rem; 
                border-radius: 8px; 
                border: 1px solid rgba(59, 130, 246, 0.2);
                margin-bottom: 1rem;
            ">
                <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
                    <strong style="color: #2563eb;">ℹ️ Viable Investment</strong><br>
                    Your IRR of {irr_pct:.1f}% is above typical cost of capital. This represents 
                    a financially viable project, though sensitivity to assumptions should be checked.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="
                background-color: rgba(239, 68, 68, 0.05); 
                padding: 1rem; 
                border-radius: 8px; 
                border: 1px solid rgba(239, 68, 68, 0.2);
                margin-bottom: 1rem;
            ">
                <div style="font-size: 1rem; color: var(--text-main); line-height: 1.6;">
                    <strong style="color: #b91c1c;">⚠️ Review Required</strong><br>
                    Your IRR of {irr_pct:.1f}% is below typical cost of capital thresholds. 
                    Consider adjusting project parameters or reviewing cost assumptions.
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ===================================================================
    # REAL-TIME SENSITIVITY ANALYSIS
    # ===================================================================
    st.markdown("---")
    st.markdown("### 🎚️ Real-Time Sensitivity Analysis")
    
    st.caption("""
    Adjust the sliders below to see how changes in key parameters affect your IRR.
    **The IRR updates instantly** without re-running the optimization.
    """)
    
    # Create two columns for sensitivity sliders
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Battery CAPEX")
        
        # CAPEX sensitivity slider
        # Range: €200-400/kWh, default is current value
        capex_sensitivity = st.slider(
            "Battery Cost (€/kWh)",
            min_value=200.0,
            max_value=400.0,
            value=bess_config['cost_eur_kwh'],
            step=10.0,
            key="capex_slider",
            help="Adjust battery cost to see impact on IRR"
        )
        
        # Show change from base
        capex_delta = capex_sensitivity - bess_config['cost_eur_kwh']
        if capex_delta != 0:
            st.caption(f"Change: {capex_delta:+.0f} €/kWh from base")
    
    with col2:
        st.markdown("#### Battery Duration")
        
        # Duration sensitivity slider
        # Range: 2-6 hours
        current_duration = bess_config['capacity_mwh'] / bess_config['power_mw']
        
        duration_sensitivity = st.slider(
            "Duration (hours)",
            min_value=2.0,
            max_value=6.0,
            value=current_duration,
            step=0.5,
            key="duration_slider",
            help="Adjust battery duration (affects capacity and CAPEX)"
        )
        
        # Show change from base
        duration_delta = duration_sensitivity - current_duration
        if duration_delta != 0:
            st.caption(f"Change: {duration_delta:+.1f} hours from base")
    
    # ===================================================================
    # CALCULATE ADJUSTED IRR
    # ===================================================================
    # Only recalculate if parameters changed
    if (capex_sensitivity != bess_config['cost_eur_kwh'] or 
        abs(duration_sensitivity - current_duration) > 0.01):
        
        # For duration change, adjust capacity while keeping power constant
        adjusted_bess_config = bess_config.copy()
        adjusted_bess_config['cost_eur_kwh'] = capex_sensitivity
        adjusted_bess_config['capacity_mwh'] = bess_config['power_mw'] * duration_sensitivity
        
        # Recalculate IRR with adjusted parameters
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
        
        # Show adjusted IRR
        irr_change = adjusted_irr - irr_pct if (adjusted_irr and irr_pct) else 0
        
        st.markdown("#### 📊 Adjusted Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(render_metric_card(
                label="Adjusted IRR",
                value=f"{adjusted_irr:.1f}%" if adjusted_irr else "N/A",
                delta=f"{irr_change:+.1f}%",
                delta_color="normal" if irr_change >= 0 else "inverse"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(render_metric_card(
                label="Adjusted NPV",
                value=f"€{adjusted_irr_result['npv_eur']/1e6:.2f}M"
            ), unsafe_allow_html=True)
        
        with col3:
            # Show new CAPEX
            st.markdown(render_metric_card(
                label="New Battery CAPEX",
                value=f"€{adjusted_irr_result['capex_bess_eur']/1e6:.2f}M"
            ), unsafe_allow_html=True)
    
    # ===================================================================
    # SENSITIVITY CHARTS
    # ===================================================================
    st.markdown("---")
    st.markdown("### 📉 IRR Sensitivity Charts")
    
    render_sensitivity_charts(
        base_irr_result=irr_result,
        pv_config=pv_config,
        bess_config=bess_config,
        scenario=scenario,
        optimized_revenue=optimized_revenue,
        baseline_revenue=baseline_revenue,
        project_lifetime=project_lifetime,
        pv_degradation=pv_degradation,
        battery_degradation=battery_degradation
    )


def render_sensitivity_charts(
    base_irr_result,
    pv_config,
    bess_config,
    scenario,
    optimized_revenue,
    baseline_revenue,
    project_lifetime,
    pv_degradation,
    battery_degradation
):
    """
    Render IRR sensitivity charts showing how IRR changes with key parameters.
    """
    
    col1, col2 = st.columns(2)
    
    # ===================================================================
    # CHART 1: IRR vs CAPEX
    # ===================================================================
    with col1:
        st.markdown("#### IRR vs. Battery CAPEX")
        
        # Generate range of CAPEX values
        capex_range = np.linspace(200, 400, 20)  # €200-400/kWh
        irr_values = []
        
        for capex in capex_range:
            adjusted_bess = bess_config.copy()
            adjusted_bess['cost_eur_kwh'] = capex
            
            result = financial_service.calculate_irr(
                scenario=scenario.lower(),
                annual_revenue_eur=optimized_revenue,
                pv_config=pv_config,
                bess_config=adjusted_bess,
                project_lifetime_years=project_lifetime,
                pv_degradation_rate=pv_degradation,
                battery_degradation_rate=battery_degradation,
                baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None
            )
            
            irr_values.append(result['irr_percent'] if result['irr_percent'] else 0)
        
        # Create figure
        fig1 = go.Figure()
        
        fig1.add_trace(go.Scatter(
            x=capex_range,
            y=irr_values,
            mode='lines',
            name='IRR',
            line=dict(color='#3b82f6', width=3)
        ))
        
        # Add current point
        fig1.add_trace(go.Scatter(
            x=[bess_config['cost_eur_kwh']],
            y=[base_irr_result['irr_percent']],
            mode='markers',
            name='Current',
            marker=dict(size=12, color='#ef4444')
        ))
        
        # Add reference line at 8% hurdle rate
        fig1.add_hline(
            y=8.0,
            line_dash="dash",
            line_color="gray",
            annotation_text="8% Hurdle Rate"
        )
        
        fig1.update_layout(
            xaxis_title="Battery CAPEX (€/kWh)",
            yaxis_title="IRR (%)",
            height=350,
            showlegend=True,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    # ===================================================================
    # CHART 2: IRR vs Duration
    # ===================================================================
    with col2:
        st.markdown("#### IRR vs. Battery Duration")
        
        # Generate range of duration values
        duration_range = np.linspace(2, 6, 20)  # 2-6 hours
        irr_values = []
        
        for duration in duration_range:
            adjusted_bess = bess_config.copy()
            adjusted_bess['capacity_mwh'] = bess_config['power_mw'] * duration
            
            result = financial_service.calculate_irr(
                scenario=scenario.lower(),
                annual_revenue_eur=optimized_revenue,
                pv_config=pv_config,
                bess_config=adjusted_bess,
                project_lifetime_years=project_lifetime,
                pv_degradation_rate=pv_degradation,
                battery_degradation_rate=battery_degradation,
                baseline_revenue_eur=baseline_revenue if scenario == "Brownfield" else None
            )
            
            irr_values.append(result['irr_percent'] if result['irr_percent'] else 0)
        
        # Create figure
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=duration_range,
            y=irr_values,
            mode='lines',
            name='IRR',
            line=dict(color='#10b981', width=3)
        ))
        
        # Add current point
        current_duration = bess_config['capacity_mwh'] / bess_config['power_mw']
        fig2.add_trace(go.Scatter(
            x=[current_duration],
            y=[base_irr_result['irr_percent']],
            mode='markers',
            name='Current',
            marker=dict(size=12, color='#ef4444')
        ))
        
        # Add reference line
        fig2.add_hline(
            y=8.0,
            line_dash="dash",
            line_color="gray",
            annotation_text="8% Hurdle Rate"
        )
        
        fig2.update_layout(
            xaxis_title="Battery Duration (hours)",
            yaxis_title="IRR (%)",
            height=350,
            showlegend=True,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
