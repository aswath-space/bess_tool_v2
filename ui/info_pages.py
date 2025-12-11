"""
Info Pages: Credits & Coverage
==============================

Simple informational pages for the footer navigation.
"""

import streamlit as st

def render_credits_page():
    """Render the Credits page."""
    st.title("⭐️ Credits & Acknowledgements")
    
    st.markdown("""
    ### Data Sources
    
    **Electricity Prices**
    - Source: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
    - Data: Day-ahead market prices (hourly)
    - License: Creative Commons Attribution 4.0 International (CC BY 4.0)
    
    **Solar Generation**
    - Source: [PVGIS (Photovoltaic Geographical Information System)](https://re.jrc.ec.europa.eu/pvg_tools/en/)
    - European Commission Joint Research Centre
    - Data: Hourly solar generation profiles based on satellite data
    
    ### Technologies
    
    **Optimization Engine**
    - [CVXPY](https://www.cvxpy.org/) - Convex optimization library for Python
    - [CLARABEL](https://github.com/oxfordcontrol/Clarabel.rs) - Primary solver for battery dispatch
    
    **Frontend & Visualization**
    - [Streamlit](https://streamlit.io/) - Web application framework
    - [Plotly](https://plotly.com/python/) - Interactive charting library
    
    ### Development Team
    
    Developed by Aswath through **Antigravity AI** for the Advanced Agentic Coding project.
    """)
    
    if st.button("← Back to App"):
        # Clear query params to return to main app
        st.query_params.clear()
        st.rerun()


def render_coverage_page():
    """Render the Coverage page."""
    st.title("🌍 Geographic Coverage")
    
    st.markdown("""
    ### Supported Regions
    
    This tool supports all European countries integrated into the ENTSO-E transparency platform. 
    
    **Primary Markets Verified:**
    - 🇩🇪 Germany (`DE_LU`)
    - 🇫🇷 France (`FR`)
    - 🇪🇸 Spain (`ES`)
    - 🇳🇱 Netherlands (`NL`)
    - 🇧🇪 Belgium (`BE`)
    - 🇦🇹 Austria (`AT`)
    - 🇵🇱 Poland (`PL`)
    
    **Data Availability:**
    - Markets with active Day-Ahead trading are supported.
    - Some smaller regions or islands may have incomplete data.
    
    ### Zone Detection
    
    The tool automatically detects the correct bidding zone based on the GPS coordinates provided.
    
    **Note on Bidding Zones:**
    - Some countries (like Italy, Norway, Sweden) are split into multiple price zones.
    - The tool attempts to map coordinates to the correct price zone.
    - If exact mapping fails, it defaults to the primary national zone.
    """)
    
    if st.button("← Back to App"):
        # Clear query params to return to main app
        st.query_params.clear()
        st.rerun()
