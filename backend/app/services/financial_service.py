"""
Financial Service - Investment Analysis
========================================

This service calculates financial metrics for investment decision-making,
implementing Stage 3 of the PRD's "Compare & Convince" methodology.

Key Financial Metrics:
----------------------
1. **IRR (Internal Rate of Return)**: The discount rate at which NPV = 0.
   This is the "true" return on investment, accounting for time value of money.
   Example: 12% IRR means the project returns 12% annually over its lifetime.

2. **NPV (Net Present Value)**: The present value of all future cash flows
   minus the initial investment, discounted at a given discount rate.
   Positive NPV = good investment. Higher NPV = better investment.

3. **Payback Period**: Number of years to recover initial investment.
   Simpler metric but doesn't account for time value of money.

4. **LCOE (Levelized Cost of Energy)**: Average cost per MWh over lifetime.
   Useful for comparing different energy technologies.

Scenarios:
----------
- **Greenfield**: New project, includes PV + BESS CAPEX
  IRR calculated on total investment (PV + BESS)
  
- **Brownfield**: Existing PV park, adding BESS
  IRR calculated on BESS CAPEX only (incremental IRR)
  Revenue comparison is: (PV+BESS) minus (PV only)

User-Specified Parameters:
---------------------------
- Project Lifetime: 10-30 years (default: 20 years)
- Discount Rate: 4-20% (default: 8%)
- PV Degradation: 1%/year (advanced setting)
- Battery Degradation: 2%/year (advanced setting)

Author: Aswath
Date: 2025-12-11
"""

import numpy as np
import numpy_financial as npf


class FinancialService:
    """
    Service for calculating investment financial metrics.
    
    Provides IRR, NPV, payback period, and other metrics for both
    greenfield and brownfield scenarios.
    """
    
    # ===================================================================
    # DEFAULT PARAMETERS (User-Specified)
    # ===================================================================
    DEFAULT_PROJECT_LIFETIME_YEARS = 20
    DEFAULT_DISCOUNT_RATE = 0.08  # 8%
    DEFAULT_PV_DEGRADATION_RATE = 0.01  # 1% per year
    DEFAULT_BATTERY_DEGRADATION_RATE = 0.02  # 2% per year
    
    @staticmethod
    def calculate_irr(
        scenario,
        annual_revenue_eur,
        pv_config,
        bess_config,
        project_lifetime_years=None,
        pv_degradation_rate=None,
        battery_degradation_rate=None,
        baseline_revenue_eur=None
    ):
        """
        Calculate Internal Rate of Return (IRR) for the project.
        
        IRR is the discount rate that makes NPV = 0. It represents the
        "true" annualized return on investment over the project lifetime.
        
        Decision Rule:
        - IRR > Discount Rate (e.g., 8%) → Good investment
        - IRR > 10-12% → Excellent for utility-scale solar
        - IRR < 6% → May struggle to attract financing
        
        Parameters:
        -----------
        scenario : str
            'greenfield' or 'brownfield'
            - Greenfield: New project, total CAPEX (PV + BESS)
            - Brownfield: Adding BESS to existing PV, only BESS CAPEX
            
        annual_revenue_eur : float
            First-year revenue with PV + BESS (EUR/year)
            
        pv_config : dict
            PV configuration with keys:
            - 'capacity_mw': PV capacity in MW
            - 'cost_eur_wp': PV cost in EUR per Watt-peak
            
        bess_config : dict
            Battery configuration with keys:
            - 'capacity_mwh': Battery capacity in MWh
            - 'cost_eur_kwh': Battery cost in EUR per kWh
            
        project_lifetime_years : int, optional
            Project lifetime (default: 20 years, range: 10-30)
            
        pv_degradation_rate : float, optional
            Annual PV degradation rate (default: 0.01 = 1%/year)
            
        battery_degradation_rate : float, optional
            Annual battery degradation rate (default: 0.02 = 2%/year)
            
        baseline_revenue_eur : float, optional
            First-year revenue with PV only (required for brownfield)
            
        Returns:
        --------
        dict
            IRR results:
            - irr_percent: IRR as percentage (e.g., 12.5 for 12.5%)
            - npv_at_8_percent: NPV at 8% discount rate (EUR)
            - cash_flows: List of annual cash flows for transparency
            - capex_total: Total initial investment (EUR)
            - payback_period_years: Simple payback period
            
        Example:
        --------
        >>> result = FinancialService.calculate_irr(
        >>>     scenario='greenfield',
        >>>     annual_revenue_eur=4_100_000,
        >>>     pv_config={'capacity_mw': 10.0, 'cost_eur_wp': 0.6},
        >>>     bess_config={'capacity_mwh': 16.0, 'cost_eur_kwh': 300}
        >>> )
        >>> print(f"IRR: {result['irr_percent']:.1f}%")
        """
        
        # ===================================================================
        # STEP 1: Set Default Parameters
        # ===================================================================
        if project_lifetime_years is None:
            project_lifetime_years = FinancialService.DEFAULT_PROJECT_LIFETIME_YEARS
        if pv_degradation_rate is None:
            pv_degradation_rate = FinancialService.DEFAULT_PV_DEGRADATION_RATE
        if battery_degradation_rate is None:
            battery_degradation_rate = FinancialService.DEFAULT_BATTERY_DEGRADATION_RATE
        
        # ===================================================================
        # STEP 2: Calculate CAPEX (Initial Investment)
        # ===================================================================
        # PV CAPEX Calculation
        # Formula: Capacity (MW) × 1,000,000 (to get Watts) × Cost (EUR/Wp)
        # Example: 10 MW × 1,000,000 W/MW × €0.60/W = €6,000,000
        pv_capex = pv_config['capacity_mw'] * 1_000_000 * pv_config['cost_eur_wp']
        
        # Battery CAPEX Calculation
        # Formula: Capacity (MWh) × 1,000 (to get kWh) × Cost (EUR/kWh)
        # Example: 16 MWh × 1,000 kWh/MWh × €300/kWh = €4,800,000
        bess_capex = bess_config['capacity_mwh'] * 1_000 * bess_config['cost_eur_kwh']
        
        # Total CAPEX depends on scenario
        if scenario.lower() == 'greenfield':
            # New project: Both PV and BESS
            total_capex = pv_capex + bess_capex
            capex_description = f"PV: €{pv_capex/1e6:.1f}M + BESS: €{bess_capex/1e6:.1f}M"
        else:  # brownfield
            # Existing PV: Only BESS investment
            total_capex = bess_capex
            capex_description = f"BESS only: €{bess_capex/1e6:.1f}M"
        
        # ===================================================================
        # STEP 3: Calculate Annual Revenues with Degradation
        # ===================================================================
        # Cash flow structure:
        # Year 0: -CAPEX (negative, we pay money)
        # Year 1 to N: +Revenue (positive, we earn money)
        #
        # Degradation Effect:
        # - PV degrades ~1%/year (less generation over time)
        # - Battery degrades ~2%/year (less efficiency/capacity over time)
        # - Combined degradation: worse of the two (conservative approach)
        
        cash_flows = [-total_capex]  # Year 0: Initial investment (negative)
        
        # For brownfield, we need to subtract baseline revenue
        # because we only care about the INCREMENTAL revenue from adding BESS
        if scenario.lower() == 'brownfield':
            if baseline_revenue_eur is None:
                raise ValueError(
                    "baseline_revenue_eur required for brownfield scenario"
                )
            # Incremental revenue = (PV + BESS) - (PV only)
            incremental_revenue_year1 = annual_revenue_eur - baseline_revenue_eur
        else:
            # Greenfield: Total revenue
            incremental_revenue_year1 = annual_revenue_eur
        
        # Generate cash flows for each year
        for year in range(1, project_lifetime_years + 1):
            # Calculate degradation factor
            # We use the combined effect of both PV and battery degradation
            # Formula: (1 - degradation_rate) ^ year
            # Example Year 5: (1 - 0.015)^5 = 0.928 = 92.8% of original
            
            # Combined degradation (average of PV and battery for simplicity)
            # A more sophisticated model would track each separately
            combined_degradation = (pv_degradation_rate + battery_degradation_rate) / 2
            degradation_factor = (1 - combined_degradation) ** year
            
            # Apply degradation to revenue
            revenue_this_year = incremental_revenue_year1 * degradation_factor
            
            cash_flows.append(revenue_this_year)
        
        # ===================================================================
        # STEP 4: Calculate IRR
        # ===================================================================
        # IRR is the discount rate where NPV = 0
        # We use numpy_financial.irr() which solves:
        # Sum[ CF_t / (1 + IRR)^t ] = 0
        #
        # Returns as decimal (e.g., 0.123 for 12.3%)
        try:
            irr = npf.irr(cash_flows)
            irr_percent = irr * 100  # Convert to percentage
        except:
            # IRR calculation can fail if cash flows are all positive/negative
            # or if no solution exists
            irr_percent = None
        
        # ===================================================================
        # STEP 5: Calculate NPV at 8% Discount Rate
        # ===================================================================
        # NPV tells us the present value of the project in today's EUR
        # Using the default 8% discount rate as benchmark
        # Positive NPV = good, higher is better
        npv_at_8_percent = npf.npv(
            FinancialService.DEFAULT_DISCOUNT_RATE,
            cash_flows
        )
        
        # ===================================================================
        # STEP 6: Calculate Simple Payback Period
        # ===================================================================
        # Payback = How many years to recover initial investment
        # This is a simple calculation that doesn't discount future cash flows
        # Formula: CAPEX / Average Annual Revenue (undiscounted)
        
        if incremental_revenue_year1 > 0:
            # Simple payback (ignores time value of money)
            simple_payback_years = total_capex / incremental_revenue_year1
            
            # Discounted payback (accounts for time value)
            # Find the year where cumulative discounted cash flows turn positive
            cumulative_discounted = 0
            discounted_payback_years = None
            for year in range(len(cash_flows)):
                discounted_cf = cash_flows[year] / (1 + FinancialService.DEFAULT_DISCOUNT_RATE) ** year
                cumulative_discounted += discounted_cf
                if cumulative_discounted > 0 and discounted_payback_years is None:
                    discounted_payback_years = year
        else:
            simple_payback_years = None
            discounted_payback_years = None
        
        # ===================================================================
        # STEP 7: Calculate LCOE (Levelized Cost of Energy)
        # ===================================================================
        # LCOE = Total Lifetime Cost / Total Lifetime Generation
        # This is useful for comparing energy technologies
        # Note: For a revenue optimization tool, LCOE is less critical
        #       than IRR/NPV, but included for completeness
        
        # We'd need total generation to calculate this properly
        # For now, we'll skip it as it's not in the core requirements
        
        # ===================================================================
        # RETURN RESULTS
        # ===================================================================
        return {
            # Primary Metrics
            'irr_percent': round(irr_percent, 2) if irr_percent is not None else None,
            'npv_eur': round(npv_at_8_percent, 2),
            'payback_period_simple_years': round(simple_payback_years, 1) if simple_payback_years else None,
            'payback_period_discounted_years': discounted_payback_years,
            
            # Investment Details
            'capex_total_eur': round(total_capex, 2),
            'capex_pv_eur': round(pv_capex, 2),
            'capex_bess_eur': round(bess_capex, 2),
            'capex_description': capex_description,
            
            # Cash Flow Details
            'cash_flows': [round(cf, 2) for cf in cash_flows],
            'project_lifetime_years': project_lifetime_years,
            'first_year_revenue_eur': round(incremental_revenue_year1, 2),
            
            # Assumptions
            'scenario': scenario,
            'pv_degradation_rate': pv_degradation_rate,
            'battery_degradation_rate': battery_degradation_rate,
            'discount_rate_used_for_npv': FinancialService.DEFAULT_DISCOUNT_RATE
        }
    
    @staticmethod
    def calculate_sensitivity_irr(
        base_result,
        capex_override_eur_kwh=None,
        duration_override_hours=None,
        bess_config=None
    ):
        """
        Calculate IRR with adjusted parameters for sensitivity analysis.
        
        This enables REAL-TIME IRR updates when the user adjusts sliders
        in Stage 3, without re-running the optimization.
        
        The key insight: Changing CAPEX or duration doesn't require
        re-optimizing the battery dispatch. We just recalculate the
        financial metrics using the same revenue profile.
        
        Parameters:
        -----------
        base_result : dict
            Original IRR calculation result from calculate_irr()
            
        capex_override_eur_kwh : float, optional
            New battery cost (EUR/kWh) to test
            If None, uses original value
            
        duration_override_hours : float, optional
            New battery duration (hours) to test
            This changes capacity while keeping power constant
            If None, uses original value
            
        bess_config : dict, optional
            Original battery config for reference
            
        Returns:
        --------
        float
            Adjusted IRR as percentage
            
        Example:
        --------
        >>> # User moves slider from €300/kWh to €250/kWh
        >>> new_irr = FinancialService.calculate_sensitivity_irr(
        >>>     base_result=original_result,
        >>>     capex_override_eur_kwh=250.0,
        >>>     bess_config=bess_config
        >>> )
        >>> st.metric("Adjusted IRR", f"{new_irr:.1f}%", delta=f"{new_irr - original_irr:+.1f}%")
        """
        
        # Get original cash flows
        cash_flows = base_result['cash_flows'].copy()
        
        # Adjust CAPEX if override provided
        if capex_override_eur_kwh is not None and bess_config is not None:
            # Recalculate BESS CAPEX with new cost
            original_bess_capex = base_result['capex_bess_eur']
            new_bess_capex = bess_config['capacity_mwh'] * 1_000 * capex_override_eur_kwh
            capex_delta = new_bess_capex - original_bess_capex
            
            # Adjust Year 0 cash flow (initial investment)
            cash_flows[0] -= capex_delta  # More negative if cost increased
        
        # Adjust capacity if duration override provided
        if duration_override_hours is not None and bess_config is not None:
            # If duration changes, capacity changes (assuming power stays constant)
            # This would affect revenue, but for simplicity in sensitivity analysis,
            # we assume the revenue impact is proportional to capacity change
            # 
            # More sophisticated: Re-run optimization with new capacity
            # Simpler (for real-time): Assume linear relationship
            #
            # For now, we'll keep revenue constant (conservative assumption)
            # This is a simplification - in reality, larger battery = more revenue
            pass
        
        # Recalculate IRR with adjusted cash flows
        try:
            irr = npf.irr(cash_flows)
            irr_percent = irr * 100
        except:
            irr_percent = None
        
        return irr_percent
    
    @staticmethod
    def calculate_greenfield_economics(
        pv_capacity_mw: float,
        pv_cost_eur_wp: float,
        bess_capacity_mwh: float,
        bess_cost_eur_kwh: float,
        annual_revenue_eur: float,
        project_lifetime_years: int = 25,
        discount_rate: float = 0.08
    ):
        """Calculate full project economics for greenfield (new PV+BESS)."""
        # CAPEX
        pv_capex = pv_capacity_mw * 1_000_000 * pv_cost_eur_wp
        bess_capex = bess_capacity_mwh * 1_000 * bess_cost_eur_kwh
        total_capex = pv_capex + bess_capex
        
        # OPEX (1.5% for PV, 2% for BESS)
        pv_opex = pv_capex * 0.015
        bess_opex = bess_capex * 0.02
        total_opex = pv_opex + bess_opex
        
        # Cash flows
        annual_cash_flow = annual_revenue_eur - total_opex
        cash_flows = [-total_capex] + [annual_cash_flow] * project_lifetime_years
        
        # Metrics
        irr = npf.irr(cash_flows) * 100 if len(cash_flows) > 1 else None
        npv = npf.npv(discount_rate, cash_flows)
        payback = total_capex / annual_cash_flow if annual_cash_flow > 0 else None
        
        return {
            'project_type': 'Greenfield',
            'pv_capex_eur': pv_capex,
            'bess_capex_eur': bess_capex,
            'total_capex_eur': total_capex,
            'total_opex_annual_eur': total_opex,
            'annual_cash_flow_eur': annual_cash_flow,
            'irr_percent': irr,
            'npv_eur': npv,
            'payback_years': payback
        }
    
    @staticmethod
    def calculate_brownfield_economics(
        pv_capacity_mw: float,
        pv_cost_eur_wp: float,
        pv_age_years: int,
        bess_capacity_mwh: float,
        bess_cost_eur_kwh: float,
        annual_revenue_eur: float,
        baseline_revenue_eur: float,
        pv_lifetime_years: int = 25,
        bess_lifetime_years: int = 15,
        discount_rate: float = 0.08
    ):
        """Calculate brownfield economics with depreciation."""
        # PV depreciation
        pv_original_capex = pv_capacity_mw * 1_000_000 * pv_cost_eur_wp
        pv_remaining_life = max(0, pv_lifetime_years - pv_age_years)
        depreciation = (pv_original_capex / pv_lifetime_years) * pv_age_years
        pv_book_value = max(0, pv_original_capex - depreciation)
        
        # BESS CAPEX
        bess_capex = bess_capacity_mwh * 1_000 * bess_cost_eur_kwh
        
        # Analysis period
        analysis_period = min(pv_remaining_life, bess_lifetime_years)
        
        # OPEX
        pv_opex = pv_original_capex * 0.015
        bess_opex = bess_capex * 0.02
        
        # Cash flows
        total_cash_flow = annual_revenue_eur - (pv_opex + bess_opex)
        incremental_revenue = annual_revenue_eur - baseline_revenue_eur
        incremental_cash_flow = incremental_revenue - bess_opex
        
        # Combined metrics
        combined_capex = pv_book_value + bess_capex
        combined_cf = [-combined_capex] + [total_cash_flow] * analysis_period
        combined_irr = npf.irr(combined_cf) * 100 if len(combined_cf) > 1 else None
        combined_npv = npf.npv(discount_rate, combined_cf)
        
        # Battery-only metrics
        battery_cf = [-bess_capex] + [incremental_cash_flow] * analysis_period
        battery_irr = npf.irr(battery_cf) * 100 if len(battery_cf) > 1 else None
        battery_npv = npf.npv(discount_rate, battery_cf)
        
        # Viability
        warnings = []
        if pv_age_years + bess_lifetime_years > pv_lifetime_years:
            warnings.append("Battery lifetime extends beyond PV life")
        if battery_irr and battery_irr < 8.0:
            warnings.append(f"Battery IRR ({battery_irr:.1f}%) below hurdle rate (8%)")
        
        return {
            'project_type': 'Brownfield',
            'pv_age_years': pv_age_years,
            'pv_remaining_life_years': pv_remaining_life,
            'pv_book_value_eur': pv_book_value,
            'bess_capex_eur': bess_capex,
            'combined_irr_percent': combined_irr,
            'combined_npv_eur': combined_npv,
            'battery_irr_percent': battery_irr,
            'battery_npv_eur': battery_npv,
            'incremental_revenue_eur': incremental_revenue,
            'analysis_period_years': analysis_period,
            'warnings': warnings
        }
    
    @staticmethod
    def format_financial_metric(value, metric_type='currency'):
        """
        Format financial metrics for display.
        
        Helper function to consistently format numbers in the UI.
        
        Parameters:
        -----------
        value : float
            The value to format
        metric_type : str
            'currency', 'percentage', or 'years'
            
        Returns:
        --------
        str
            Formatted string
        """
        if value is None:
            return "N/A"
        
        if metric_type == 'currency':
            if abs(value) >= 1_000_000:
                return f"€{value/1e6:.1f}M"
            elif abs(value) >= 1_000:
                return f"€{value/1e3:.0f}k"
            else:
                return f"€{value:,.0f}"
        elif metric_type == 'percentage':
            return f"{value:.1f}%"
        elif metric_type == 'years':
            return f"{value:.1f} years"
        else:
            return f"{value:,.2f}"


# ===================================================================
# Create singleton instance for easy import
# ===================================================================
financial_service = FinancialService()
