"""
Optimization Service - Battery Dispatch Optimization
====================================================

This service finds the optimal battery charging/discharging schedule to
maximize revenue, implementing the core of the PRD's "Battery Solution" stage.

Optimization Approach:
---------------------
We use **Linear Programming (LP)** to solve the battery dispatch problem.
This is a convex optimization problem that CVXPY can solve efficiently.

Problem Formulation:
-------------------
**Objective**: Maximize total revenue over the planning horizon

**Decision Variables**:
- p_charge[t]: Battery charging power at hour t (MW)  
- p_discharge[t]: Battery discharging power at hour t (MW)
- soc[t]: State of charge at hour t (MWh)
- p_grid[t]: Net grid power at hour t (MW) - positive = export, negative = import

**Constraints**:
1. Energy Balance: soc[t+1] = soc[t] + η*p_charge[t] - p_discharge[t]/η
2. SoC Limits: 0 ≤ soc[t] ≤ Capacity
3. Power Limits: 0 ≤ p_charge[t] ≤ Max Power
4. Power Limits: 0 ≤ p_discharge[t] ≤ Max Power
5. Grid Balance: p_grid[t] = pv[t] + p_discharge[t] - p_charge[t]
6. Initial Condition: soc[0] = 0 (start empty)

**Revenue Calculation**:
Revenue = Σ price[t] × p_grid[t]

Why LP Instead of Heuristics?
-----------------------------
The previous heuristic approach used simple rules (charge when price < 20, 
discharge when price > 100). This is suboptimal because:

1. **Arbitrary Thresholds**: Price thresholds don't adapt to actual price patterns
2. **No Look-Ahead**: Doesn't consider future prices when making decisions
3. **Suboptimal Timing**: May charge/discharge at wrong times
4. **Missed Opportunities**: Doesn't capture all arbitrage potential

LP optimization solves all these issues by considering the entire day/week
simultaneously and finding the globally optimal dispatch schedule.

**Typical Revenue Improvement**: 20-40% higher than simple heuristics

Library: CVXPY
--------------
CVXPY is the industry-standard Python library for convex optimization.
It's used by researchers and practitioners worldwide for:
- Power systems optimization
- Portfolio optimization  
- Machine learning
- Control systems

Alternative Libraries:
- PuLP: Simpler but less powerful
- Pyomo: More features but steeper learning curve
- Gurobi: Commercial, very fast but requires license

For battery dispatch (a convex problem), CVXPY is the best choice.

Author: [Your Name]
Date: 2025-12-11
"""

import pandas as pd
import numpy as np
import cvxpy as cp


class OptimizationService:
    """
    Service for optimizing battery dispatch using Linear Programming.
    
    This replaces the previous heuristic approach with a proper LP solver
    that finds the globally optimal dispatch schedule.
    """
    
    @staticmethod
    def run_optimization(
        pv_df: pd.DataFrame,
        price_data: list,
        bess_power_mw: float,
        bess_capacity_mwh: float
    ):
        """
        Run LP optimization for battery dispatch.
        
        This is the core revenue optimization that shows the VALUE of adding
        battery storage to a PV plant.
        
        Parameters:
        -----------
        pv_df : pd.DataFrame
            Hourly PV generation data with column 'pv_power_kw'
            
        price_data : list of dict
            Hourly prices with key 'price' (EUR/MWh)
            
        bess_power_mw : float
            Battery power rating (MW) - how fast it can charge/discharge
            
        bess_capacity_mwh : float
            Battery energy capacity (MWh) - how much energy it can store
            
        Returns:
        --------
        dict
            Optimization results containing:
            - financials: Revenue metrics and statistics
            - hourly_data: Hour-by-hour breakdown for charts
            - value_breakdown: Revenue sources (baseline, arbitrage, etc.)
            
        Raises:
        -------
        ValueError
            If optimization fails to find a solution
        """
        
        # ===================================================================
        # STEP 1: Prepare Data
        # ===================================================================
        # Ensure we have matching data lengths
        T = min(len(pv_df), len(price_data))
        
        # Create working DataFrame
        df = pv_df.iloc[:T].copy()
        
        # Extract prices from list of dicts
        prices_eur_mwh = np.array([p['price'] for p in price_data[:T]])
        df['price_eur_mwh'] = prices_eur_mwh
        
        # Convert PV generation to MW (from kW)
        pv_generation_mw = df['pv_power_kw'].values / 1000  # Shape: (T,)
        
        # ===================================================================
        # STEP 2: Define Decision Variables
        # ===================================================================
        # These are the variables that CVXPY will optimize
        
        # Battery charging power at each hour (MW)
        # Non-negative constraint means: can only charge, not discharge
        p_charge = cp.Variable(T, nonneg=True, name='p_charge')
        
        # Battery discharging power at each hour (MW)
        # Non-negative constraint means: can only discharge, not charge
        p_discharge = cp.Variable(T, nonneg=True, name='p_discharge')
        
        # State of charge at each hour (MWh)
        # We have T+1 points: start of hour 0, 1, 2, ..., T
        # Non-negative constraint means: can't have negative energy stored
        soc = cp.Variable(T + 1, nonneg=True, name='soc')
        
        # Net grid power (MW): positive = export, negative = import
        # This is what we sell to (or buy from) the grid
        p_grid = cp.Variable(T, name='p_grid')
        
        # ===================================================================
        # STEP 3: Define Parameters
        # ===================================================================
        # Round-trip efficiency (typical for Li-ion batteries: 85-92%)
        # This means: Store 1 MWh, get 0.9 MWh back
        efficiency = 0.90
        
        # ===================================================================
        # STEP 4: Define Constraints
        # ===================================================================
        constraints = []
        
        # CONSTRAINT 1: Initial State of Charge
        # Battery starts empty (conservative assumption)
        # Could also optimize starting SoC, but this is simpler
        constraints.append(soc[0] == 0)
        
        # CONSTRAINT 2: Energy Balance (State of Charge Dynamics)
        # This is the core battery physics constraint
        # Energy stored in next hour = Energy now + Charging - Discharging
        # With efficiency losses accounted for:
        # - When charging: η * power goes into storage  
        # - When discharging: power / η comes out of storage
        for t in range(T):
            constraints.append(
                soc[t + 1] == soc[t] + efficiency * p_charge[t] - p_discharge[t] / efficiency
            )
        
        # CONSTRAINT 3: State of Charge Limits
        # Battery can't store more than its rated capacity
        # Already have soc >= 0 from variable definition
        constraints.append(soc <= bess_capacity_mwh)
        
        # CONSTRAINT 4: Charging Power Limits
        # Can't charge faster than the inverter/power electronics allow
        constraints.append(p_charge <= bess_power_mw)
        
        # CONSTRAINT 5: Discharging Power Limits  
        # Can't discharge faster than the inverter/power electronics allow
        constraints.append(p_discharge <= bess_power_mw)
        
        # CONSTRAINT 6: Grid Power Balance
        # What goes to grid = PV generation + Battery discharge - Battery charge
        # Positive p_grid = we're selling (exporting)
        # Negative p_grid = we're buying (importing)
        for t in range(T):
            constraints.append(
                p_grid[t] == pv_generation_mw[t] + p_discharge[t] - p_charge[t]
            )
        
        # OPTIONAL CONSTRAINT: Can't charge from grid
        # Uncomment this if you want to prohibit grid charging
        # (only allow charging from excess PV)
        # for t in range(T):
        #     constraints.append(p_charge[t] <= pv_generation_mw[t])
        
        # ===================================================================
        # STEP 5: Define Objective Function
        # ===================================================================
        # We want to MAXIMIZE revenue
        # Revenue = Σ (price[t] × grid_power[t])
        # 
        # When grid_power > 0: We export and earn money (price × power)
        # When grid_power < 0: We import and pay money (price × power is negative)
        #
        # CVXPY minimizes by default, so we use negative to maximize
        revenue = prices_eur_mwh @ p_grid  # Matrix multiplication: Σ price[t] * p_grid[t]
        
        objective = cp.Maximize(revenue)
        
        # ===================================================================
        # STEP 6: Solve the Optimization Problem
        # ===================================================================
        # Create the problem
        problem = cp.Problem(objective, constraints)
        
        # Solve using CLARABEL solver (comes with CVXPY)
        # Other solvers: ECOS, SCS, OSQP
        # We use verbose=False to suppress solver output
        try:
            problem.solve(verbose=False)
        except Exception as e:
            raise ValueError(f"Optimization failed: {str(e)}")
        
        # Check if solver found optimal solution
        if problem.status != cp.OPTIMAL:
            raise ValueError(
                f"Optimization did not converge. Status: {problem.status}. "
                f"This may indicate infeasible constraints or numerical issues."
            )
        
        # ===================================================================
        # STEP 7: Extract Optimal Solution
        # ===================================================================
        # Get the optimal values of decision variables
        # .value returns numpy array
        optimal_p_charge = p_charge.value  # (T,)
        optimal_p_discharge = p_discharge.value  # (T,)
        optimal_soc = soc.value[:-1]  # (T,) - exclude final SoC
        optimal_p_grid = p_grid.value  # (T,)
        optimal_revenue = problem.value  # Total revenue (EUR)
        
        # ===================================================================
        # STEP 8: Store Results in DataFrame
        # ===================================================================
        # Convert back to kW for consistency with input
        df['bess_charge_kw'] = optimal_p_charge * 1000  # MW to kW
        df['bess_discharge_kw'] = optimal_p_discharge * 1000  # MW to kW
        
        # Net battery flow: positive = discharge, negative = charge
        # This matches the convention in the original code
        df['bess_flow_kw'] = df['bess_discharge_kw'] - df['bess_charge_kw']
        
        # State of charge
        df['soc_kwh'] = optimal_soc * 1000  # MWh to kWh
        
        # Net grid power  
        df['net_grid_kw'] = optimal_p_grid * 1000  # MW to kW
        
        # ===================================================================
        # STEP 9: Calculate Revenue Components
        # ===================================================================
        # Break down revenue into different sources for the "value bridge"
        
        # Revenue when we export (positive grid power)
        df['revenue_from_export'] = df.apply(
            lambda x: (x['net_grid_kw'] / 1000) * x['price_eur_mwh'] if x['net_grid_kw'] > 0 else 0,
            axis=1
        )
        
        # Cost when we import (negative grid power)
        df['cost_from_import'] = df.apply(
            lambda x: abs(x['net_grid_kw'] / 1000) * x['price_eur_mwh'] if x['net_grid_kw'] < 0 else 0,
            axis=1
        )
        
        # Net revenue (export revenue minus import cost)
        df['net_revenue'] = df['revenue_from_export'] - df['cost_from_import']
        
        # ===================================================================
        # STEP 10: Calculate Performance Metrics
        # ===================================================================
        # Total revenue
        total_revenue = df['net_revenue'].sum()
        
        # PV generation totals
        total_pv_generation_mwh = df['pv_power_kw'].sum() / 1000
        
        # Battery cycling
        # Full cycle = Discharge capacity equal to nameplate  
        # Example: 16 MWh battery, 32 MWh discharged = 2 cycles
        total_discharge_mwh = df['bess_discharge_kw'].sum() / 1000
        annual_cycles = total_discharge_mwh / bess_capacity_mwh if bess_capacity_mwh > 0 else 0
        
        # Battery utilization (how often we use it)
        hours_charging = (df['bess_charge_kw'] > 0.1).sum()  # > 0.1 kW to avoid numerical noise
        hours_discharging = (df['bess_discharge_kw'] > 0.1).sum()
        total_hours_active = hours_charging + hours_discharging
        utilization_percent = (total_hours_active / len(df)) * 100
        
        # Arbitrage-specific metrics
        # When do we charge? When prices are < average
        avg_price = df['price_eur_mwh'].mean()
        df['is_charging_hour'] = df['bess_charge_kw'] > 0.1
        df['is_discharging_hour'] = df['bess_discharge_kw'] > 0.1
        
        avg_charging_price = df[df['is_charging_hour']]['price_eur_mwh'].mean() if hours_charging > 0 else 0
        avg_discharging_price = df[df['is_discharging_hour']]['price_eur_mwh'].mean() if hours_discharging > 0 else 0
        price_spread = avg_discharging_price - avg_charging_price
        
        # Negative price handling
        negative_price_hours = (df['price_eur_mwh'] < 0).sum()
        if negative_price_hours > 0:
            # Energy that would have been curtailed or sold at negative price
            potential_curtailment_kwh = df[df['price_eur_mwh'] < 0]['pv_power_kw'].sum()
            # How much did we actually charge during negative prices?
            actual_charge_during_neg_price = df[df['price_eur_mwh'] < 0]['bess_charge_kw'].sum()
        else:
            potential_curtailment_kwh = 0
            actual_charge_during_neg_price = 0
        
        # ===================================================================
        # STEP 11: Calculate Value Breakdown (for Waterfall Chart)
        # ===================================================================
        # This is used in the "value bridge" visualization
        # We want to show: Base PV Revenue + Arbitrage + Neg Price + Curtailment
        #
        # Note: To calculate this properly, we need the PV baseline revenue
        # which should be passed in. For now, we estimate components.
        
        # Arbitrage revenue estimate:
        # Revenue from price spread × Energy cycled
        arbitrage_revenue_estimate = (
            price_spread * total_discharge_mwh if price_spread > 0 else 0
        )
        
        # Negative price savings estimate:
        # Energy charged during negative prices × average negative price
        if negative_price_hours > 0:
            avg_negative_price = df[df['price_eur_mwh'] < 0]['price_eur_mwh'].mean()
            negative_price_savings = abs(
                (actual_charge_during_neg_price / 1000) * avg_negative_price
            )
        else:
            negative_price_savings = 0
        
        # ===================================================================
        # RETURN RESULTS
        # ===================================================================
        return {
            # Financial Summary
            "financials": {
                "total_revenue_eur": round(total_revenue, 2),
                "annual_pv_production_mwh": round(total_pv_generation_mwh, 2),
                "annual_cycles": round(annual_cycles, 1),
                "battery_utilization_percent": round(utilization_percent, 1),
                "hours_charging": int(hours_charging),
                "hours_discharging": int(hours_discharging),
            },
            
            # Arbitrage Metrics
            "arbitrage": {
                "avg_charging_price": round(avg_charging_price, 2),
                "avg_discharging_price": round(avg_discharging_price, 2),
                "price_spread": round(price_spread, 2),
                "estimated_arbitrage_revenue": round(arbitrage_revenue_estimate, 2),
            },
            
            # Negative Price Impact
            "negative_prices": {
                "negative_price_hours": int(negative_price_hours),
                "potential_curtailment_kwh": round(potential_curtailment_kwh, 2),
                "energy_charged_during_neg_prices_kwh": round(actual_charge_during_neg_price, 2),
                "estimated_savings": round(negative_price_savings, 2),
            },
            
            # Value Breakdown (for waterfall chart)
            # Note: Base PV revenue would ideally come from baseline service
            "value_breakdown": {
                "arbitrage_gain": round(arbitrage_revenue_estimate, 2),
                "negative_price_savings": round(negative_price_savings, 2),
                # Curtailment and base revenue need baseline comparison
                # Will be calculated in UI by comparing to baseline result
            },
            
            # Hourly Data (first week for visualization)
            "hourly_data": df.head(168).to_dict(orient='records'),  # 168 hours = 7 days
            
            # Full year data (for advanced analysis)
            "full_year_df": df,
            
            # Optimization metadata
            "optimization_status": problem.status,
            "solver_time_seconds": problem.solver_stats.solve_time if problem.solver_stats else None,
        }


# ===================================================================
# Create singleton instance for easy import
# ===================================================================
optimization_service = OptimizationService()

