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
    ### Data & Core Libraries   
    
    **Electricity Markets**
    - Data: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) (CC BY 4.0)
    - Client: [entsoe-py](https://github.com/EnergieID/entsoe-py) (MIT)
    
    **Solar Generation**
    - Data Source: [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0)
    - Simulation Engine: [pvlib python](https://pvlib-python.readthedocs.io/) (BSD-3-Clause)
    - *Weather data provided by Open-Meteo.com under CC BY 4.0 license.*
    
    ### Optimization Stack
    
    **Engine**
    - [CVXPY](https://www.cvxpy.org/) (Apache 2.0) - Modeling language
    - [HiGHS](https://highs.dev/) (MIT) - Mixed-Integer Linear Programming (MILP) solver
    
    ### Application Framework
    
    - Frontend: [Streamlit](https://streamlit.io/) (Apache 2.0)
    - Visualization: [Plotly](https://plotly.com/python/) (MIT)
    - Data Processing: [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/) (BSD-3-Clause)
    
    ### Development Team
    Developed by Aswath through **Antigravity AI**.
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
