"""
Auto-Sizing Service - Smart Battery Defaults
=============================================

This service provides intelligent recommendations for battery system sizing
based on the PV installation characteristics. This implements the PRD's
"Smart Defaults" feature for the battery upsell stage.

Key Concepts:
-------------
1. **Power Rating (MW)**: How fast the battery can charge/discharge.
   Rule of thumb: 20-40% of PV capacity to handle midday generation.

2. **Duration (hours)**: How long the battery can discharge at full power.
   Common values: 2-4 hours for daily arbitrage applications.

3. **Capacity (MWh)**: Total energy storage = Power × Duration.
   Example: 4 MW × 4 hours = 16 MWh

4. **C-Rate**: The ratio of power to capacity (1/Duration).
   Example: 4h duration = 0.25 C-rate (can fully charge/discharge in 4h)

Sizing Philosophy:
------------------
- Conservative: Smaller battery, lower risk, certain ROI
- Moderate: Balanced approach (DEFAULT)
- Aggressive: Larger battery, higher potential revenue, more risk

Author: [Your Name]
Date: 2025-12-11
"""

import numpy as np


class AutoSizingService:
    """
    Service for automatically sizing battery storage systems.
    
    Provides smart defaults and multiple sizing options based on
    PV system characteristics and user risk preferences.
    """
    
    # ===================================================================
    # CONFIGURATION CONSTANTS
    # ===================================================================
    # These values are based on industry best practices for utility-scale
    # PV+BESS systems. They can be adjusted based on market conditions.
    
    # Power Sizing (as percentage of PV capacity)
    POWER_RATIO_CONSERVATIVE = 0.20  # 20% of PV
    POWER_RATIO_MODERATE = 0.40      # 40% of PV (USER DEFAULT)
    POWER_RATIO_AGGRESSIVE = 0.60    # 60% of PV
    
    # Duration Options (hours)
    DURATION_SHORT = 2.0      # 2 hours - for intraday arbitrage
    DURATION_MEDIUM = 4.0     # 4 hours - balanced (USER DEFAULT)
    DURATION_LONG = 6.0       # 6 hours - for longer price spreads
    
    @staticmethod
    def calculate_smart_defaults(pv_capacity_mw, mode='moderate'):
        """
        Calculate recommended battery specifications based on PV capacity.
        
        This implements the "Smart Defaults" feature where the system
        suggests optimal battery sizing based on the PV park size.
        
        Parameters:
        -----------
        pv_capacity_mw : float
            PV system capacity in MW (e.g., 10.0 for 10 MW)
            
        mode : str, optional
            Sizing philosophy: 'conservative', 'moderate', or 'aggressive'
            Default is 'moderate' as specified by user (40% power ratio)
            
        Returns:
        --------
        dict
            Recommended battery specifications:
            - power_mw: Recommended power rating (MW)
            - duration_hours: Recommended duration (hours)
            - capacity_mwh: Calculated capacity (MWh)
            - c_rate: Calculated C-rate (1/hours)
            - mode: The sizing mode used
            - rationale: Explanation of the recommendation
            
        Example:
        --------
        >>> defaults = AutoSizingService.calculate_smart_defaults(10.0)
        >>> print(f"Recommended: {defaults['power_mw']} MW / {defaults['capacity_mwh']} MWh")
        >>> # Output: "Recommended: 4.0 MW / 16.0 MWh"
        """
        
        # ===================================================================
        # STEP 1: Select Power Ratio Based on Mode
        # ===================================================================
        if mode.lower() == 'conservative':
            power_ratio = AutoSizingService.POWER_RATIO_CONSERVATIVE
            duration = AutoSizingService.DURATION_SHORT
            rationale = """
            **Conservative Sizing**
            - Lower upfront CAPEX
            - Proven ROI with less market risk
            - Suitable for risk-averse investors
            - Focuses on high-certainty arbitrage opportunities
            """
        elif mode.lower() == 'aggressive':
            power_ratio = AutoSizingService.POWER_RATIO_AGGRESSIVE
            duration = AutoSizingService.DURATION_LONG
            rationale = """
            **Aggressive Sizing**
            - Higher upfront CAPEX
            - Maximizes revenue potential
            - Suitable for markets with high price volatility
            - Captures extended price spread opportunities
            """
        else:  # moderate (DEFAULT)
            power_ratio = AutoSizingService.POWER_RATIO_MODERATE
            duration = AutoSizingService.DURATION_MEDIUM
            rationale = f"""
            **Moderate Sizing (Recommended)**
            - Balanced risk-reward profile
            - Standard industry practice for PV+BESS
            - Power: {power_ratio:.0%} of PV capacity
            - Duration: {duration} hours for daily arbitrage cycles
            - Optimizes both curtailment recovery and arbitrage
            """
        
        # ===================================================================
        # STEP 2: Calculate Power Rating
        # ===================================================================
        # Formula: Battery Power (MW) = PV Capacity (MW) × Power Ratio
        # Example: 10 MW PV × 0.40 = 4 MW battery
        power_mw = pv_capacity_mw * power_ratio
        
        # ===================================================================
        # STEP 3: Calculate Capacity
        # ===================================================================
        # Formula: Capacity (MWh) = Power (MW) × Duration (hours)
        # Example: 4 MW × 4 hours = 16 MWh
        capacity_mwh = power_mw * duration
        
        # ===================================================================
        # STEP 4: Calculate C-Rate
        # ===================================================================
        # C-Rate describes how fast the battery charges/discharges
        # Formula: C-Rate = 1 / Duration
        # Example: 1 / 4 hours = 0.25 C (can fully charge in 4 hours)
        # 
        # Interpretation:
        # - 1.0 C-rate = can fully charge/discharge in 1 hour
        # - 0.5 C-rate = takes 2 hours for full charge/discharge
        # - 0.25 C-rate = takes 4 hours for full charge/discharge
        c_rate = 1 / duration if duration > 0 else 0
        
        # ===================================================================
        # STEP 5: Round to Practical Values
        # ===================================================================
        # In practice, battery systems come in standard sizes
        # We round to reasonable increments for commercial systems
        power_mw = round(power_mw * 2) / 2  # Round to nearest 0.5 MW
        capacity_mwh = round(capacity_mwh * 2) / 2  # Round to nearest 0.5 MWh
        
        # ===================================================================
        # RETURN RECOMMENDATIONS
        # ===================================================================
        return {
            'power_mw': power_mw,
            'duration_hours': duration,
            'capacity_mwh': capacity_mwh,
            'c_rate': round(c_rate, 3),
            'mode': mode,
            'power_ratio': power_ratio,
            'rationale': rationale.strip()
        }
    
    @staticmethod
    def get_all_sizing_options(pv_capacity_mw):
        """
        Get all three sizing options (conservative, moderate, aggressive).
        
        This allows users to compare different sizing strategies in a
        collapsible section, as specified in the user requirements.
        
        Parameters:
        -----------
        pv_capacity_mw : float
            PV system capacity in MW
            
        Returns:
        --------
        dict
            Dictionary with three keys: 'conservative', 'moderate', 'aggressive'
            Each containing the sizing specifications from calculate_smart_defaults()
            
        Example:
        --------
        >>> options = AutoSizingService.get_all_sizing_options(10.0)
        >>> for mode, specs in options.items():
        >>>     print(f"{mode}: {specs['power_mw']} MW / {specs['capacity_mwh']} MWh")
        """
        return {
            'conservative': AutoSizingService.calculate_smart_defaults(
                pv_capacity_mw, 'conservative'
            ),
            'moderate': AutoSizingService.calculate_smart_defaults(
                pv_capacity_mw, 'moderate'
            ),
            'aggressive': AutoSizingService.calculate_smart_defaults(
                pv_capacity_mw, 'aggressive'
            )
        }
    
    @staticmethod
    def validate_battery_sizing(power_mw, capacity_mwh, pv_capacity_mw):
        """
        Validate user-specified battery sizing and provide warnings if needed.
        
        This helps users avoid common sizing mistakes that could lead to
        poor economics or technical issues.
        
        Parameters:
        -----------
        power_mw : float
            User-specified battery power (MW)
        capacity_mwh : float
            User-specified battery capacity (MWh)
        pv_capacity_mw : float
            PV system capacity (MW)
            
        Returns:
        --------
        dict
            Validation results:
            - is_valid: bool - Whether sizing is within reasonable bounds
            - warnings: list of str - Any warnings about the sizing
            - recommendations: list of str - Suggestions for improvement
            
        Example:
        --------
        >>> validation = AutoSizingService.validate_battery_sizing(8.0, 16.0, 10.0)
        >>> if not validation['is_valid']:
        >>>     for warning in validation['warnings']:
        >>>         st.warning(warning)
        """
        warnings = []
        recommendations = []
        is_valid = True
        
        # Calculate derived metrics
        power_ratio = power_mw / pv_capacity_mw if pv_capacity_mw > 0 else 0
        duration = capacity_mwh / power_mw if power_mw > 0 else 0
        
        # ===================================================================
        # CHECK 1: Power Ratio (vs PV capacity)
        # ===================================================================
        if power_ratio > 1.0:
            warnings.append(
                f"⚠️ Battery power ({power_mw} MW) exceeds PV capacity ({pv_capacity_mw} MW). "
                f"This is unusual and may indicate oversizing."
            )
            recommendations.append(
                f"Consider reducing battery power to {pv_capacity_mw * 0.6:.1f} MW "
                f"for better economics."
            )
        elif power_ratio < 0.15:
            warnings.append(
                f"⚠️ Battery power ({power_mw} MW) is very small relative to PV "
                f"({power_ratio:.0%} of PV capacity). Limited revenue potential."
            )
            recommendations.append(
                f"Consider increasing to at least {pv_capacity_mw * 0.2:.1f} MW "
                f"for meaningful impact."
            )
        
        # ===================================================================
        # CHECK 2: Duration
        # ===================================================================
        if duration > 8.0:
            warnings.append(
                f"⚠️ Battery duration ({duration:.1f} hours) is very long. "
                f"Daily arbitrage cycles rarely require >6 hours."
            )
            recommendations.append(
                "Consider reducing duration to 4-6 hours to optimize CAPEX/revenue ratio."
            )
        elif duration < 1.5:
            warnings.append(
                f"⚠️ Battery duration ({duration:.1f} hours) is very short. "
                f"May limit arbitrage opportunities."
            )
            recommendations.append(
                "Consider increasing duration to at least 2 hours for better flexibility."
            )
        
        # ===================================================================
        # CHECK 3: Absolute Size Reasonableness
        # ===================================================================
        if capacity_mwh < 1.0:
            warnings.append(
                f"⚠️ Battery capacity ({capacity_mwh} MWh) is below typical "
                f"commercial scale (1+ MWh)."
            )
            is_valid = False
        
        if power_mw < 0.5:
            warnings.append(
                f"⚠️ Battery power ({power_mw} MW) is below typical "
                f"commercial scale (0.5+ MW)."
            )
            is_valid = False
        
        # ===================================================================
        # CHECK 4: C-Rate (technical limitation)
        # ===================================================================
        c_rate = 1 / duration if duration > 0 else 0
        if c_rate > 1.0:
            warnings.append(
                f"⚠️ C-rate ({c_rate:.2f}C) is above 1.0, which may stress "
                f"battery cells and reduce lifetime."
            )
            recommendations.append(
                "Consider increasing capacity to reduce C-rate below 1.0C."
            )
        
        return {
            'is_valid': is_valid and len(warnings) == 0,
            'has_warnings': len(warnings) > 0,
            'warnings': warnings,
            'recommendations': recommendations,
            'metrics': {
                'power_ratio': round(power_ratio, 3),
                'duration': round(duration, 2),
                'c_rate': round(c_rate, 3)
            }
        }


# ===================================================================
# Create singleton instance for easy import
# ===================================================================
auto_sizing_service = AutoSizingService()
