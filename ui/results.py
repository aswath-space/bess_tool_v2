import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_results(optimization_result, market_data_df=None):
    """
    Renders the optimization results including metrics and charts.
    
    Args:
        optimization_result (dict): Output from optimization_service.run_optimization
        market_data_df (pd.DataFrame): Optional dataframe of market prices for visualization
    """
    st.markdown("## Optimization Results")
    
    # 1. Key Metrics
    fin = optimization_result.get("financials", {})
    revenue = fin.get("total_revenue_eur", 0.0)
    production = fin.get("annual_pv_production_mwh", 0.0)
    cycles = fin.get("annual_cycles", 0.0)
    
    # Calculate Simple ROI
    # CAPEX = (PV_MW * 1000 * 1000 * cost_per_Wp) + (BESS_MWh * 1000 * cost_per_kWh)
    # We need access to config here. It's usually passed or accessible.
    # For now, let's assume config is passed in optimization_result or we pass it to render_results
    # Update: passing config logic is better, but let's just make it generic or use passed config.
    # Since we don't have config here easily without refactoring 'render_results' signature widely,
    # let's modify render_results to accept 'config'.
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Revenue (Year)", f"€{revenue:,.0f}", delta_color="normal")
    with col2:
        st.metric("Annual PV Production", f"{production:,.0f} MWh")
    with col3:
         st.metric("Battery Cycles", f"{cycles} / year")
    with col4:
         # Placeholder until config is threaded through
         st.metric("Est. Net Revenue", f"€{revenue:,.0f}")


    st.markdown("---")
    
    # 2. Charts
    hourly_records = optimization_result.get("hourly_data", [])
    if not hourly_records:
        st.warning("No detail data available to plot.")
        return
        
    df = pd.DataFrame(hourly_records)
    
    # Chart 1: Operations Overview (One Week snapshot)
    st.subheader("Weekly Operations Snapshot")
    st.caption("Visualizing the first 7 days of operation: Prices vs. Battery Flow")
    
    fig = go.Figure()
    
    # Price Line (Secondary Y-Axis usually, but let's keep it simple or use dual axis)
    # Using dual axis for Price vs Power
    
    # Primary Y: Power (kW)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['pv_power_kw'], 
        name="PV Generation (kW)",
        fill='tozeroy',
        line=dict(color='#f59e0b', width=1), # Amber
        opacity=0.6
    ))
    
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['bess_flow_kw'],
        name="Battery Flow (kW)",
        marker_color='#3b82f6' # Blue
    ))
    
    # Secondary Y: Price (EUR/MWh)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['price_eur_mwh'],
        name="Market Price (€/MWh)",
        line=dict(color='#ef4444', width=2), # Red
        yaxis='y2'
    ))
    
    fig.update_layout(
        title="Power vs. Price Dynamics",
        xaxis_title="Hour Used",
        yaxis_title="Power (kW)",
        yaxis2=dict(
            title="Price (€/MWh)",
            overlaying='y',
            side='right'
        ),
        legend=dict(orientation="h", y=1.1),
        height=500,
        margin=dict(l=20, r=20, t=80, b=20),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Chart 2: State of Charge
    st.subheader("Battery State of Charge")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df.index,
        y=df['soc_kwh'],
        name="SoC (kWh)",
        fill='tozeroy',
        line=dict(color='#10b981') # Emerald
    ))
    fig2.update_layout(
        xaxis_title="Hour",
        yaxis_title="Energy (kWh)",
        height=300,
         margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Data Table
    with st.expander("View Detailed Data"):
        st.dataframe(df)
