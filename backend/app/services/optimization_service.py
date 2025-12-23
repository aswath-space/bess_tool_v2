"""
Optimization Service - Battery Dispatch Optimization
====================================================

This service finds the optimal battery charging/discharging schedule to
maximize revenue, implementing the core of the PRD's "Battery Solution" stage.

Optimization Approach:
---------------------
We use **Mixed-Integer Linear Programming (MILP)** to solve the battery dispatch problem.
This formulation uses binary variables to enforce physical constraints (mutual exclusivity
of charging and discharging), which CVXPY solves using specialized solvers (HIGHS, CBC).

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

Why MILP Instead of Heuristics or Simple LP?
--------------------------------------------
The previous heuristic approach used simple rules (charge when price < 20,
discharge when price > 100). This is suboptimal because:

1. **Arbitrary Thresholds**: Price thresholds don't adapt to actual price patterns
2. **No Look-Ahead**: Doesn't consider future prices when making decisions
3. **Suboptimal Timing**: May charge/discharge at wrong times
4. **Missed Opportunities**: Doesn't capture all arbitrage potential

Simple LP without binary variables can produce physically impossible solutions
where the battery charges and discharges simultaneously. MILP with binary
variables enforces strict mutual exclusivity between charging and discharging.

MILP optimization solves all these issues by considering the entire year
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

For battery dispatch with physical constraints, CVXPY with MILP is the best choice.

Author: Aswath
Date: 2025-12-11
"""

import pandas as pd
import numpy as np
import cvxpy as cp


class OptimizationService:
    """
    Service for optimizing battery dispatch using Mixed-Integer Linear Programming.

    This replaces the previous heuristic approach with a proper MILP solver
    that finds the globally optimal dispatch schedule while enforcing physical
    constraints (no simultaneous charging and discharging).
    """
    
    @staticmethod
    def run_optimization(
        pv_df: pd.DataFrame,
        price_data: list,
        bess_power_mw: float,
        bess_capacity_mwh: float,
        min_soc_percent: float = 0.05,
        throughput_cost_eur_mwh: float = 10.0
    ):
        """
        Run MILP optimization for battery dispatch.
        
        Uses Mixed-Integer Linear Programming to strict prevent simultaneous 
        charging and discharging, and includes degradation penalties.
        
        Parameters:
        -----------
        pv_df : pd.DataFrame
            Hourly PV generation data with column 'pv_power_kw'
        price_data : list of dict
            Hourly prices with key 'price' (EUR/MWh)
        bess_power_mw : float
            Battery power rating (MW)
        bess_capacity_mwh : float
            Battery energy capacity (MWh)
        min_soc_percent : float
            Minimum energy reserve as fraction of capacity (default 0.05 = 5%)
        throughput_cost_eur_mwh : float
            Degradation cost per MWh of throughput (charge + discharge) (default 10 EUR/MWh)
            
        Returns:
        --------
        dict
            Optimization results
        """
        
        # ===================================================================
        # STEP 1: Prepare Data
        # ===================================================================
        T = min(len(pv_df), len(price_data))
        df = pv_df.iloc[:T].copy()
        
        prices_eur_mwh = np.array([p['price'] for p in price_data[:T]])
        df['price_eur_mwh'] = prices_eur_mwh

        pv_generation_mw = np.array(df['pv_power_kw'].values, dtype=float) / 1000  # Shape: (T,)
        
        # ===================================================================
        # STEP 2: Define Decision Variables (MILP)
        # ===================================================================
        
        # Continuous variables
        p_charge = cp.Variable(T, nonneg=True, name='p_charge')
        p_discharge = cp.Variable(T, nonneg=True, name='p_discharge')
        soc = cp.Variable(T + 1, nonneg=True, name='soc')
        p_grid = cp.Variable(T, name='p_grid')
        
        # Binary variables for charging/discharging state
        # 1 if charging/discharging, 0 otherwise
        is_charging = cp.Variable(T, boolean=True, name='is_charging')
        is_discharging = cp.Variable(T, boolean=True, name='is_discharging')
        
        # ===================================================================
        # STEP 3: Define Parameters
        # ===================================================================
        efficiency = 0.90
        min_soc_mwh = bess_capacity_mwh * min_soc_percent
        
        # ===================================================================
        # STEP 4: Define Constraints
        # ===================================================================
        constraints = []
        
        # 4.1 Initial Condition
        constraints.append(soc[0] == min_soc_mwh) # Start at min SOC (conservative)
        
        # 4.2 Energy Balance
        for t in range(T):
            constraints.append(
                soc[t + 1] == soc[t] + efficiency * p_charge[t] - p_discharge[t] / efficiency
            )
        
        # 4.3 SoC Limits
        constraints.append(soc >= min_soc_mwh)
        constraints.append(soc <= bess_capacity_mwh)
        
        # 4.4 Mutually Exclusive Charge/Discharge (The "Big-M" constraints)
        # We use the binary variables to enforce:
        # if is_charging[t] == 1, then p_discharge[t] MUST be 0
        # if is_discharging[t] == 1, then p_charge[t] MUST be 0
        
        # Logical constraint: Cannot be charging AND discharging at same time
        constraints.append(is_charging + is_discharging <= 1)
        
        # Coupling constraints linking continuous power to binary state
        # p_charge[t] <= P_max * is_charging[t]
        # If is_charging is 0, p_charge must be 0. If 1, p_charge can be up to P_max.
        constraints.append(p_charge <= bess_power_mw * is_charging)
        constraints.append(p_discharge <= bess_power_mw * is_discharging)
        
        # 4.5 Grid Balance
        for t in range(T):
            constraints.append(
                p_grid[t] == pv_generation_mw[t] + p_discharge[t] - p_charge[t]
            )
            
        # ===================================================================
        # STEP 5: Define Objective Function
        # ===================================================================
        # Maximize: Market Revenue - Throughput Cost (Degradation)
        
        market_revenue = prices_eur_mwh @ p_grid
        
        # Throughput cost applies to both charging and discharging
        # total_throughput = sum(p_charge) + sum(p_discharge)
        # We subtract this cost from revenue
        degradation_penalty = throughput_cost_eur_mwh * (cp.sum(p_charge) + cp.sum(p_discharge))
        
        total_profit = market_revenue - degradation_penalty
        
        objective = cp.Maximize(total_profit)
        
        # ===================================================================
        # STEP 6: Solve (MILP)
        # ===================================================================
        problem = cp.Problem(objective, constraints)
        
        try:
            # Use HIGHS solver for MILP if available, otherwise CBC or SCIP
            # CVXPY should pick the best installed MILP solver automatically if we don't specify,
            # but specifying helps debugging.
            
            solver_opts = {'verbose': False}
            installed = list(cp.installed_solvers())
            if 'HIGHS' in installed:
                problem.solve(solver=cp.HIGHS, **solver_opts)
            elif 'CBC' in installed:
                problem.solve(solver=cp.CBC, **solver_opts)
            else:
                # Fallback to default (likely GLPK_MI if installed, or error)
                print("Warning: No specific MILP solver found (HIGHS/CBC). Letting CVXPY choose.")
                problem.solve(**solver_opts)
                 
        except Exception as e:
            raise ValueError(f"Optimization failed: {str(e)}")
        
        if problem.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
            raise ValueError(f"Optimization failed with status: {problem.status}")
             
        # ===================================================================
        # STEP 7: Extract Results
        # ===================================================================
        if p_charge.value is None or p_discharge.value is None or soc.value is None or p_grid.value is None:
            raise ValueError("Optimization failed: solution variables are None")

        optimal_p_charge = np.array(p_charge.value, dtype=float)
        optimal_p_discharge = np.array(p_discharge.value, dtype=float)
        optimal_soc = np.array(soc.value[:-1], dtype=float)
        optimal_p_grid = np.array(p_grid.value, dtype=float)

        # Recalculate financial metrics (Revenue without penalty for display)
        # We want to show the user the pure market revenue, and perhaps show degradation as a cost line item
        realized_revenue = np.sum(prices_eur_mwh * optimal_p_grid)

        # ===================================================================
        # STEP 8: Store Results
        # ===================================================================
        df['bess_charge_kw'] = optimal_p_charge * 1000
        df['bess_discharge_kw'] = optimal_p_discharge * 1000
        df['bess_flow_kw'] = df['bess_discharge_kw'] - df['bess_charge_kw']
        df['soc_kwh'] = optimal_soc * 1000
        df['net_grid_kw'] = optimal_p_grid * 1000
        
        # Revenue calculation
        df['revenue_from_export'] = df.apply(
            lambda x: (x['net_grid_kw'] / 1000) * x['price_eur_mwh'] if x['net_grid_kw'] > 0 else 0,
            axis=1
        )
        df['cost_from_import'] = df.apply(
            lambda x: abs(x['net_grid_kw'] / 1000) * x['price_eur_mwh'] if x['net_grid_kw'] < 0 else 0,
            axis=1
        )
        df['net_revenue'] = df['revenue_from_export'] - df['cost_from_import']
        
        # Financial Tally
        total_revenue = df['net_revenue'].sum()
        total_throughput_mwh = (df['bess_charge_kw'].sum() + df['bess_discharge_kw'].sum()) / 1000
        total_degradation_cost = total_throughput_mwh * throughput_cost_eur_mwh
        
        net_profit = total_revenue - total_degradation_cost
        
        # Metrics
        total_pv_generation_mwh = df['pv_power_kw'].sum() / 1000
        total_discharge_mwh = df['bess_discharge_kw'].sum() / 1000
        annual_cycles = total_discharge_mwh / bess_capacity_mwh if bess_capacity_mwh > 0 else 0
        
        hours_charging = (df['bess_charge_kw'] > 0.1).sum()
        hours_discharging = (df['bess_discharge_kw'] > 0.1).sum()
        utilization_percent = ((hours_charging + hours_discharging) / len(df)) * 100
        
        # Arbitrage
        df['is_charging_hour'] = df['bess_charge_kw'] > 0.1
        df['is_discharging_hour'] = df['bess_discharge_kw'] > 0.1
        
        avg_charging_price = df[df['is_charging_hour']]['price_eur_mwh'].mean() if hours_charging > 0 else 0
        avg_discharging_price = df[df['is_discharging_hour']]['price_eur_mwh'].mean() if hours_discharging > 0 else 0
        price_spread = avg_discharging_price - avg_charging_price
        
        # Negative prices
        negative_price_hours = (df['price_eur_mwh'] < 0).sum()
        if negative_price_hours > 0:
            potential_curtailment_kwh = df[df['price_eur_mwh'] < 0]['pv_power_kw'].sum()
            actual_charge_during_neg_price = df[df['price_eur_mwh'] < 0]['bess_charge_kw'].sum()
        else:
            potential_curtailment_kwh = 0
            actual_charge_during_neg_price = 0
             
        # Estimated Arbitrage Revenue
        # (Discharge Energy * Discharge Price) - (Charge Energy * Charge Price)
        # Accurate calculation based on actual flows
        arbitrage_revenue_exact = (
            (df[df['is_discharging_hour']]['bess_discharge_kw']/1000 * df[df['is_discharging_hour']]['price_eur_mwh']).sum() -
            (df[df['is_charging_hour']]['bess_charge_kw']/1000 * df[df['is_charging_hour']]['price_eur_mwh']).sum()
        )
             
        return {
            "financials": {
                "total_revenue_eur": round(total_revenue, 2),
                "total_degradation_cost_eur": round(total_degradation_cost, 2),
                "net_profit_eur": round(net_profit, 2), # Revenue - Degradation
                "annual_pv_production_mwh": round(total_pv_generation_mwh, 2),
                "annual_cycles": round(annual_cycles, 1),
                "battery_utilization_percent": round(utilization_percent, 1),
                "hours_charging": int(hours_charging),
                "hours_discharging": int(hours_discharging),
            },
            "arbitrage": {
                "avg_charging_price": round(avg_charging_price, 2),
                "avg_discharging_price": round(avg_discharging_price, 2),
                "price_spread": round(price_spread, 2),
                "estimated_arbitrage_revenue": round(arbitrage_revenue_exact, 2),
            },
            "negative_prices": {
                "negative_price_hours": int(negative_price_hours),
                "potential_curtailment_kwh": round(potential_curtailment_kwh, 2),
                "energy_charged_during_neg_prices_kwh": round(actual_charge_during_neg_price, 2),
                # Calculate savings: Sum of (Charge * -Price) for negative price hours
                # In our revenue calculation, Cost = Grid_Import * Price. If Price < 0, Cost < 0 (Gain).
                # So Savings = - (Sum of Cost when Price < 0 and Grid < 0)
                # Simplified: Sum of abs(Price) * Charge_MWh
                "estimated_savings": round(
                    abs(
                        (df[df['price_eur_mwh'] < 0]['bess_charge_kw']/1000 * df[df['price_eur_mwh'] < 0]['price_eur_mwh']).sum()
                    ), 2
                ),
            },
            "value_breakdown": {
                "arbitrage_gain": round(arbitrage_revenue_exact, 2),
                # Degradation is a cost, effectively reducing gain
                "degradation_loss": round(total_degradation_cost, 2), 
            },
            "hourly_data": df.head(168).to_dict(orient='records'),
            "full_year_df": df,
            "optimization_status": problem.status,
            "solver_time_seconds": problem.solver_stats.solve_time if problem.solver_stats else None,
        }


# ===================================================================
# Create singleton instance for easy import
# ===================================================================
optimization_service = OptimizationService()

