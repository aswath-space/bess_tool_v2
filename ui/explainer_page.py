"""
Theory & Concepts Explainer Page
=================================

This page provides comprehensive theoretical background for the PV-BESS
Revenue Optimization Tool.

Author: Antigravity AI
Date: 2025-12-11
"""

import streamlit as st
import plotly.graph_objects as go


def render_explainer_page():
    """Render the complete theory and concepts explainer page."""
    
    st.title("📚 Theory & Concepts")
    st.markdown("""
    Understanding the economic and technical foundations behind PV-BESS optimization.
    """)
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Solar Cannibalization",
        "Battery Economics",
        "Optimization Method",
        "Market Dynamics",
        "Financial Metrics"
    ])
    
    with tab1:
        render_cannibalization_theory()
    
    with tab2:
        render_battery_economics()
    
    with tab3:
        render_optimization_theory()
    
    with tab4:
        render_market_dynamics()
    
    with tab5:
        render_financial_metrics()


def render_cannibalization_theory():
    """Explain solar cannibalization effect."""
    
    st.header("☀️ Solar Cannibalization Effect")
    
    st.markdown("""
    ### What is Solar Cannibalization?
    
    As solar penetration increases in electricity markets, a paradoxical effect emerges:
    **more solar capacity leads to lower revenues per unit**. This is called the
    "solar cannibalization effect" or "value deflation."
    
    ### Why Does This Happen?
    
    1. **Solar generates during the same hours** (midday when the sun shines)
    2. **Increased supply during those hours** pushes prices down
    3. **Generators sell at lower prices** despite producing the same energy
    4. **Revenue per MWh declines** as more solar is added to the grid
    
    ### Key Metrics
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Capture Price
        
        The **weighted average price** a solar plant receives, weighted by its generation:
        """)
        
        st.latex(r'''
        P_{capture} = \frac{\sum_{t=1}^{8760} (Gen_t \times Price_t)}{\sum_{t=1}^{8760} Gen_t}
        ''')
        
        st.markdown("""
        This reflects what the solar plant **actually earns** per MWh.
        """)
    
    with col2:
        st.markdown("""
        #### Baseload Price
        
        The **simple average price** across all hours:
        """)
        
        st.latex(r'''
        P_{baseload} = \frac{\sum_{t=1}^{8760} Price_t}{8760}
        ''')
        
        st.markdown("""
        This is what a 24/7 power plant would earn per MWh.
        """)
    
    st.markdown("""
    ### Capture Rate: The Critical Metric
    
    The **capture rate** is the ratio of capture price to baseload price:
    
    st.latex(r'''
    Capture\ Rate = \frac{P_{capture}}{P_{baseload}} \times 100\%
    ''')
    
    **Interpretation:**
    - **90%+**: Excellent - minimal cannibalization
    - **70-90%**: Moderate - typical for mature solar markets
    - **<70%**: Significant - battery storage highly recommended
    
    ### How Battery Storage Helps
    
    Battery storage mitigates cannibalization by:
    
    1. **Time-shifting generation**: Store midday solar, sell during evening peaks
    2. **Avoiding negative prices**: Charge when prices are negative (instead of paying to export)
    3. **Capturing arbitrage**: Buy low, sell high using price spreads
    4. **Increasing effective capture rate**: Better alignment with high-price hours
    """)
    
    # Simple visualization
    st.markdown("### Visualization: Price vs Generation Profile")
    
    import numpy as np
    hours = np.arange(24)
    solar_gen = np.maximum(0, np.sin((hours - 6) *np.pi / 12) * 100)
    prices = 80 - solar_gen * 0.3 + np.random.normal(0, 5, 24)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=solar_gen, name="Solar Generation",
        fill='tozeroy', line=dict(color='orange')
    ))
    fig.add_trace(go.Scatter(
        x=hours, y=prices, name="Market Price",
        line=dict(color='red', width=2), yaxis='y2'
    ))
    
    fig.update_layout(
        title="Solar Generation vs Market Prices (Typical Day)",
        xaxis_title="Hour of Day",
        yaxis_title="Generation (MW)",
        yaxis2=dict(title="Price (€/MWh)", overlaying='y', side='right'),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("""
    **Notice:** Solar generates most during hours 10-16, but this is exactly when
    prices are lowest due to  oversupply. Battery storage shifts this energy to
    high-price evening hours (17-21).
    """)


def render_battery_economics():
    """Explain battery economics and value streams."""
    
    st.header("🔋 Battery Storage Economics")
    
    st.markdown("""
    ### Battery Value Streams
    
    Battery storage creates value through multiple mechanisms:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 1. Energy Arbitrage
        
        **Buy low, sell high**
        
        - Charge during low-price hours
        - Discharge during high-price hours
        - Profit = Price Spread × Energy × Efficiency
        
        **Example:**
        - Charge at €30/MWh (midnight)
        - Discharge at €120/MWh (evening peak)
        - Spread: €90/MWh
        - With 90% efficiency: €81/MWh profit
        
        #### 2. Negative Price Mitigation
        
        **Avoid paying to export**
        
        - Charge when prices go negative
        - Get paid to charge (negative price)
        - Discharge later for positive revenue
        - Double benefit: avoid loss + earn revenue
        """)
    
    with col2:
        st.markdown("""
        #### 3. Cannibalization Recovery
        
        **Shift generation to better hours**
        
        - Store low-value midday solar
        - Sell during high-value evening hours
        - Recover lost cannibalization value
        - Improves effective capture rate
        
        #### 4. Grid Services (Future)
        
        **Additional revenue streams**
        
        - Frequency regulation
        - Capacity market payments
        - Voltage support
        - Black start capability
        """)
    
    st.markdown("""
    ---
    
    ### Battery Duration: Power vs Energy
    
    Understanding the difference between **power** and **energy** is crucial:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### Power (MW)
        
        **How fast** the battery can charge or discharge
        
        - Measured in Megawatts (MW)
        - Determined by inverter capacity
        - Affects arbitrage opportunity capture
        - Higher power = faster response
        """)
    
    with col2:
        st.markdown("""
        #### Energy (MWh)
        
        **How much** the battery can store
        
        - Measured in Megawatt-hours (MWh)
        - Determined by battery cell capacity
        - Affects duration of discharge
        - Higher capacity = longer duration
        """)
    
    with col3:
        st.markdown("""
        #### Duration (Hours)
        
        **How long** at full power
        
        - Duration = Energy ÷ Power
        - Example: 16 MWh ÷ 4 MW = 4 hours
        - Typical range: 1-6 hours
        - 4 hours optimal for solar+storage
        """)
    
    st.markdown("""
    ---
    
    ### Economic Considerations
    
    #### Capital Costs (CAPEX)
    
    - **Battery cells**: €150-250/kWh (declining)
    - **Inverter**: €50-100/kWh
    - **Balance of system**: €50-100/kWh
    - **Total installed cost**: €250-350/kWh (2025)
    - **Trending down**: ~15% per year
    
    #### Operating Costs (OPEX)
    
    - **O&M**: 1-2% of CAPEX per year
    - **Insurance**: 0.5-1% of CAPEX per year
    - **Degradation**: Capacity loss over time
    - **Replacement**: After 10-15 years
    
    #### Lifetime & Degradation
    
    - **Calendar life**: 15-20 years
    - **Cycle life**: 5,000-10,000 cycles 
    - **Degradation rate**: 2-3% per year based on cycles and depth of discharge
    - **Warranty**: Typically 10 years, 70% capacity
    
    ---
    
    ### Round-Trip Efficiency (RTE)
    
    The percentage of energy put into the battery that can be retrieved.
    
    st.latex(r'''
    RTE = \frac{Energy_{out}}{Energy_{in}} \times 100\%
    ''')
    
    **Typical values (2025):**
    - Lithium-ion (LFP): 92-95%
    - Flow batteries: 70-80%
    - Hydrogen: 30-40%
    
    Our model assumes **90% AC-to-AC efficiency**, accounting for inverter losses, auxiliary consumption (HVAC), and cell hysteresis.
    """)


def render_optimization_theory():
    """Explain Mixed-Integer Linear Programming optimization approach."""
    
    st.header("⚡ Optimization Method: MILP")
    
    st.markdown("""
    ### Why Optimization Matters
    
    The battery dispatch problem is complex:
    - Thousands of decisions (charge/discharge every hour)
    - Interconnected constraints (energy balance, power limits)
    - Need to consider future prices (look-ahead optimization)
    - **Physical Reality**: Batteries cannot charge and discharge simultaneously.
    
    **Mixed-Integer Linear Programming (MILP)** finds the mathematically optimal solution while enforcing strict physical constraints.
    
    ---
    
    ### Problem Formulation
    
    #### Objective Function
    
    **Maximize Net Profit (Revenue - Degradation):**
    
    ```
    Maximize: Σ (Price[t] × Grid_Power[t]) - Σ (Throughput_Cost × (Charge[t] + Discharge[t]))
    ```
    
    Where:
    - `Price[t]` = Market price at hour t (€/MWh)
    - `Grid_Power[t]` = Net power to grid (MW)
    - `Throughput_Cost` = Degradation penalty (e.g., €10/MWh) avoiding unnecessary cycling
    
    #### Decision Variables
    
    What the optimizer chooses:
    
    - `Charge[t]` (Continuous): Battery charging power (MW)
    - `Discharge[t]` (Continuous): Battery discharging power (MW)
    - `Is_Charging[t]` (Binary): 1 if charging, 0 otherwise
    - `Is_Discharging[t]` (Binary): 1 if discharging, 0 otherwise
    - `SoC[t]` (Continuous): State of charge (MWh)
    
    #### Constraints
    
    Physical and operational limits:
    
    **1. Binary Logic (Mutually Exclusive):**
    st.latex(r'''
    Is\_Charging_t + Is\_Discharging_t \le 1
    ''')
    st.caption("Ensures battery never charges and discharges at the same time.")
    
    **2. Power Limits:**
    st.latex(r'''
    0 \le Charge_t \le P_{max} \times Is\_Charging_t
    ''')
    st.latex(r'''
    0 \le Discharge_t \le P_{max} \times Is\_Discharging_t
    ''')
    
    **3. Energy Balance:**
    st.latex(r'''
    SoC_{t+1} = SoC_t + (\eta \times Charge_t) - \frac{Discharge_t}{\eta}
    ''')
    
    **4. State of Charge Limits:**
    st.latex(r'''
    SoC_{min} \le SoC_t \le SoC_{max}
    ''')
    st.caption("We enforce a minimum reserve (e.g., 5%) to protect battery health.")
    
    ---
    
    ### Why MILP is Superior
    
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### ❌ Heuristic Rules / Simple LP
        
        **Problems:**
        - **Simultaneous Flow:** Simple LP can charge/discharge at same time to exploit math artifacts
        - **Arbitrary Thresholds:** Heuristics miss complex opportunities
        - **Unrealistic Cycling:** Ignores degradation costs
        
        **Result:**
        - Physically impossible schedules
        - Inflated revenue estimates
        """)
    
    with col2:
        st.markdown("""
        #### ✅ Rigorous MILP (Optimal)
        
        **Advantages:**
        - **Strict Physics:** Binary variables enforce realistic behavior
        - **Degradation Aware:** Penalizes unnecessary cycles
        - **Global Optimum:** Finds best possible schedule
        - **Look-Ahead:** Optimizes for future prices
        
        **Result:**
        - Accurate, bankable revenue projections
        - Realistic operations profile
        """)
    
    st.markdown("""
    ---
    
    ### Solver: CVXPY
    
    We use **CVXPY**, an industry-standard Python library for convex optimization.
    
    **Why CVXPY?**
    - Open-source and free
    - Highly reliable (used in research and industry)
    - Fast solvers (ECOS, CLARABEL, OSQP)
    - Proven track record in energy optimization
    - Active development and support
    
    **Alternatives considered:**
    - **PuLP**: Simpler but less powerful
    - **Pyomo**: More features but complex
    - **Gurobi**: Commercial, faster but requires license
    
    **Performance:**
    - Solves 1 year (8,760 hours) in < 1 second
    - Handles hundreds of constraints
    - Guaranteed to find optimal solution (if feasible)
    """)


def render_market_dynamics():
    """Explain electricity market dynamics."""
    
    st.header("💰 Electricity Market Dynamics")
    
    st.markdown("""
    ### Day-Ahead Market
    
    The **day-ahead market** is where most electricity trading occurs:
    
    #### How It Works
    
    1. **Day before delivery** (D-1): Generators and consumers submit bids
    2. **Market clearing**: Supply and demand curves intersect
    3. **Price discovery**: Clearing price set for each hour
    4. **Schedule publication**: Final dispatch schedule published
    5. **Day of delivery** (D): Physical delivery occurs
    
    #### Price Formation
    
    Electricity prices reflect:
    - **Supply**: Available capacity (coal, gas, nuclear, renewables)
    - **Demand**: Consumption patterns (residential, industrial)
    - **Transmission**: Grid constraints and congestion
    - **Weather**: Temperature (heating/cooling) and wind/solar output
    - **Fuel costs**: Gas prices, carbon prices
    
    ---
    
    ### Price Patterns
    
    #### Daily Patterns
    
    - **Night (00:00-06:00)**: Low demand, low prices
    - **Morning ramp (06:00-08:00)**: Demand increases
    - **Midday (11:00-15:00)**: High solar, prices drop
    - **Evening peak (17:00-21:00)**: High demand, high prices
    - **Night ramp-down (21:00-00:00)**: Demand decreases
    
    #### Seasonal Patterns
    
    - **Summer**: Lower demand, more solar, lower prices
    - **Winter**: Higher demand (heating), higher prices
    - **Spring/Fall**: Moderate prices
    
    #### Weather Impact
    
    - **High wind**: Prices drop (more supply)
    - **Low wind**: Prices rise (less supply)
    - **Sunny days**: Midday price cannibalization
    - **Cloudy days**: Less solar impact
    
    ---
    
    ### Renewable Integration Challenges
    
    #### Duck Curve Problem
    
    As solar penetration increases:
    
    1. **Midday oversupply**: Solar floods the market
    2. **Price depression**: Wholesale prices crash
    3. **Evening ramp**: Steep demand increase after sunset
    4. **Ramping challenge**: Conventional plants struggle to ramp up quickly
    
    **Battery storage solution:** Absorb midday oversupply, discharge during evening ramp.
    
    #### Negative Prices
    
    **When do they occur?**
    - High renewable generation + low demand
    - Grid constraints (can't transmit power)
    - Nuclear plants (can't quickly shut down)
    
    **Why stay negative?**
    - Shutdown costs > negative price costs
    - Renewable subsidies create incentive to produce
    - Grid stability requires minimum generation
    
    **Battery opportunity:**
    - Get paid to charge (negative price = revenue)
    - Discharge later at positive price
    - Double benefit from price swing
    
    ---
    
    ### ENTSO-E Transparency Platform
    
    **Data source** for this tool: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
    
    **What is ENTSO-E?**
    - European Network of Transmission System Operators for Electricity
    - Coordinates cross-border electricity flows
    - Publishes market data for transparency
    
    **Data available:**
    - Day-ahead prices (hourly)
    - Actual load and generation
    - Cross-border flows
    - Installed capacity
    - Renewable generation forecasts
    
    **Market zones:**
    - DE_LU: Germany-Luxembourg
    - FR: France
    - ES: Spain
    - IT: Italy (multiple bidding zones)
    - And many more...
    """)


def render_financial_metrics():
    """Explain financial metrics used in investment analysis."""
    
    st.header("📊 Financial Metrics Explained")
    
    st.markdown("""
    ### Key Investment Metrics
    
    Understanding the financial returns of your PV-BESS investment:
    """)
    
    # IRR
    st.markdown("""
    ---
    
    #### Internal Rate of Return (IRR)
    
    **Definition:** The discount rate at which NPV = 0 (break-even rate)
    
    **Formula:**
    st.latex(r'''
    0 = -CAPEX + \sum_{t=1}^{T} \frac{CashFlow_t}{(1 + IRR)^t}
    ''')
    
    **Interpretation:**
    - **15%+**: Excellent return, very attractive
    - **10-15%**: Good return, typical for renewables
    - **8-10%**: Moderate return, acceptable
    - **<8%**: Low return, may not justify risk
    
    **Use case:**
    - Compare to hurdle rate (required return)
    - Compare to alternative investments
    - Assess project viability
    
    **Advantages:**
    - Industry standard metric
    - Easy to understand (percentage return)
    - Accounts for time value of money
    
    **Limitations:**
    - Assumes reinvestment at IRR (unrealistic)
    - Can have multiple solutions for complex cash flows
    - Doesn't show absolute value (€)
    """)
    
    # NPV
    st.markdown("""
    ---
    
    #### Net Present Value (NPV)
    
    **Definition:** Present value of all cash flows minus initial investment
    
    **Formula:**
    st.latex(r'''
    NPV = -CAPEX + \sum_{t=1}^{T} \frac{CashFlow_t}{(1 + WACC)^t}
    ''')
    
    Where WACC = Weighted Average Cost of Capital (discount rate)
    
    **Interpretation:**
    - **NPV > 0**: Project creates value, accept
    - **NPV = 0**: Break-even, indifferent
    - **NPV < 0**: Project destroys value, reject
    
    **Use case:**
    - Absolute value creation (€)
    - Compare mutually exclusive projects
    - Capital budgeting decisions
    
    **Advantages:**
    - Shows absolute value in euros
    - Consistent with shareholder value maximization
    - Additive (can sum NPVs of projects)
    
    **Limitations:**
    - Requires accurate discount rate (WACC)
    - Harder to interpret than IRR (€ vs %)
    - Sensitive to discount rate assumptions
    """)
    
    # Payback
    st.markdown("""
    ---
    
    #### Payback Period
    
    **Definition:** Time required to recover initial investment
    
    **Formula:**
    ```
    Payback = Year when Σ Cash_Flows = CAPEX
    ```
    
    **Simple Payback:** Ignores time value of money (just sum cash flows)  
    **Discounted Payback:** Accounts for time value (uses discounted cash flows)
    
    **Interpretation:**
    - **<5 years**: Very fast payback, low risk
    - **5-8 years**: Good payback, moderate risk
    - **8-12 years**: Acceptable for long-term assets
    - **>12 years**: Slow payback, high risk
    
    **Use case:**
    - Quick risk assessment
    - Liquidity concerns
    - Communication with non-financial stakeholders
    
    **Advantages:**
    - Simple to calculate and understand
    - Good proxy for risk (faster = lower risk)
    - Useful for liquidity-constrained projects
    
    **Limitations:**
    - Ignores cash flows after payback
    - Doesn't account for scale of investment
    - No consideration of profitability beyond payback
    """)
    
    # LCOE
    st.markdown("""
    ---
    
    #### Levelized Cost of Energy (LCOE)
    
    **Definition:** Average cost per MWh over project lifetime
    
    **Formula:**
    ```
    LCOE = (CAPEX + Σ (OPEX[t] / (1 + r)^t)) / Σ (Generation[t] / (1 + r)^t)
    ```
    
    **Interpretation:**
    - Cost to produce 1 MWh of electricity
    - Compare to market prices for viability
    - Benchmark against other technologies
    
    **Typical LCOEs (2025):**
    - Solar PV: €30-50/MWh
    - Onshore wind: €40-60/MWh
    - Natural gas: €70-100/MWh
    - Coal: €80-120/MWh
    
    **Use case:**
    - Technology comparison
    - Policy analysis
    - Long-term price forecasting
    """)
    
    # WACC
    st.markdown("""
    ---
    
    #### Weighted Average Cost of Capital (WACC)
    
    **Definition:** Blended cost of debt and equity financing
    
    **Formula:**
    ```
    WACC = (E/V) × Cost_of_Equity + (D/V) × Cost_of_Debt × (1 - Tax_Rate)
    ```
    
    Where:
    - E = Market value of equity
    - D = Market value of debt
    - V = E + D (total value)
    
    **Typical WACCs:**
    - **Renewables (low risk)**: 4-6%
    - **Conventional power**: 6-8%
    - **Emerging technologies**: 8-12%
    
    **Use case:**
    - Discount rate for NPV calculation
    - Hurdle rate for IRR comparison
    - Reflects project risk and financing structure
    
    **Components:**
    - **Cost of Equity**: Return required by shareholders (8-12%)
    - **Cost of Debt**: Interest rate on loans (3-5%)
    - **Tax shield**: Debt interest is tax-deductible
    """)
    
    # Greenfield vs Brownfield
    st.markdown("""
    ---
    
    ### Greenfield vs Brownfield
    
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Greenfield Project
        
        **Definition:** New project built from scratch
        
        **Characteristics:**
        - Both PV and BESS are new
        - Total CAPEX: PV + BESS
        - Full project lifetime (25+ years)
        - Integrated design optimization
        - Single implementation
        
        **Financial Analysis:**
        - Combined PV+BESS economics
        - Total project IRR
        - Blended LCOE
        - Synergies in construction/permitting
        
        **Risk Profile:**
        - Development risk
        - Construction risk
        - Technology risk
        - Market risk
        """)
    
    with col2:
        st.markdown("""
        #### Brownfield Project
        
        **Definition:** Adding BESS to existing PV
        
        **Characteristics:**
        - PV already operational
        - Only BESS CAPEX is new
        - PV has remaining lifetime
        - Retrofit constraints
        - Incremental implementation
        
        **Financial Analysis:**
        - Incremental BESS revenues
        - Battery-specific IRR
        - Remaining PV life matters
        - Depreciated PV value
        
        **Risk Profile:**
        - Lower development risk
        - Integration challenges
        - PV age/degradation risk
        - Shortened analysis period
        """)
    
    st.markdown("""
    ---
    
    ### Cash Flow Components
    
    #### Revenue Streams
    
    - **Energy sales**: Day-ahead market revenue
    - **Capacity payments**: Grid service compensation (future)
    - **Ancillary services**: Frequency regulation, voltage support (future)
    - **Feed-in tariffs**: Fixed-price contracts (decreasing)
    - **PPAs**: Power purchase agreements with off-takers
    
    #### Cost Components
    
    **CAPEX (Capital Expenditure):**
    - PV modules and mounting
    - Inverters and transformers
    - Battery cells and BMS
    - Grid connection
    - Land acquisition/lease
    - Development and permitting
    - Construction and installation
    
    **OPEX (Operating Expenditure):**
    - O&M (operations & maintenance): 1-2% of CAPEX/year
    - Insurance: 0.5-1% of CAPEX/year
    - Land lease: €1,000-5,000/hectare/year  
    - Grid connection fees: Variable
    - Property taxes: Variable by location
    - Battery replacement reserve: Plan for Year 10-15
    
    #### Tax Considerations
    
    - **Depreciation**: Reduces taxable income (accelerated schedules available)
    - **Tax credits**: Investment tax credits (ITC) in some jurisdictions
    - **VAT**: Recoverable for commercial projects
    - **Corporate tax**: Typically 20-30% on profits
    """)


# Export for use in main app
if __name__ == "__main__":
    render_explainer_page()
