import streamlit as st

def render_inputs():
    """
    Renders the inputs in a responsive grid layout (removing sidebar dependency).
    Returns the configuration dictionary and the run button state.
    """
    st.markdown("### Project Configuration")
    
    with st.expander("Configure Asset Parameters", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📍 Location")
            lat = st.number_input("Latitude", value=52.5200, format="%.4f", help="Decimal degrees")
            lon = st.number_input("Longitude", value=13.4050, format="%.4f", help="Decimal degrees")
            
            st.markdown("#### 🔋 Battery Storage (BESS)")
            bess_capacity = st.number_input("Capacity (MWh)", value=20.0, step=1.0)
            bess_power = st.number_input("Power (MW)", value=5.0, step=0.5)
            
            st.markdown("#### 💰 Financial Assumptions (CAPEX)")
            battery_cost = st.number_input("Battery Cost (€/kWh)", value=300.0, step=10.0, help="Fully installed cost including inverter")
            pv_cost = st.number_input("PV Cost (€/Wp)", value=0.6, step=0.05, help="Turnkey PV park cost")

        with col2:
            st.markdown("#### ☀️ PV System")
            pv_capacity = st.number_input("PV Capacity (MW)", value=10.0, step=0.5, min_value=0.1)
            pv_tilt = st.slider("Tilt Angle (°)", min_value=0.0, max_value=90.0, value=35.0)
            pv_azimuth = st.slider("Azimuth (°)", min_value=-180.0, max_value=180.0, value=0.0, help="0 = South, 90 = West, -90 = East")
        
        st.markdown("---")
        run_btn = st.button("Run Revenue Optimization", type="primary", use_container_width=True)
        
    return {
        "lat": lat,
        "lon": lon,
        "pv_capacity_mw": pv_capacity,
        "pv_tilt": pv_tilt,
        "pv_azimuth": pv_azimuth,
        "bess_capacity_mwh": bess_capacity,
        "bess_power_mw": bess_power,
        "capex_battery_eur_kwh": battery_cost,
        "capex_pv_eur_wp": pv_cost
    }, run_btn
