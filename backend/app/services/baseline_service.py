"""
Baseline Service - PV-Only Revenue Calculation
================================================

This service calculates the baseline revenue scenario for a PV-only project
WITHOUT battery storage. This serves as the "anchor" in the PRD's 
"Compare & Convince" methodology.

Key Concepts:
-------------
1. **Capture Price**: The weighted average price that the PV system actually
   receives, weighted by when it generates energy. Solar typically generates
   most during midday when prices are lower.

2. **Baseload Price**: The simple average price over all hours. This is what
   a baseload power plant (running 24/7) would receive.

3. **Cannibalization**: The difference between baseload and capture price.
   As more solar is added to the grid, it pushes down midday prices,
   reducing the effective revenue per MWh. This is also called the
   "solar cannibalization effect."

4. **Capture Rate**: The ratio of capture price to baseload price.
   A capture rate of 72% means the solar plant only captures 72% of
   the average market price due to its generation profile.

Author: Aswath
Date: 2025-12-11
"""

import pandas as pd
import numpy as np


class BaselineService:
    """
    Service for calculating PV baseline performance metrics.
    
    This class provides methods to analyze the revenue and performance
    of a PV system without battery storage, including calculating the
    cannibalization effect that battery storage aims to mitigate.
    """
    
    @staticmethod
    def calculate_pv_baseline(pv_df, price_data):
        """
        Calculate comprehensive PV-only baseline metrics.
        
        This is the first step in the user journey - showing what the PV
        system earns on its own, before considering battery storage.
        
        Parameters:
        -----------
        pv_df : pd.DataFrame
            DataFrame with hourly PV generation data from PVGIS.
            Must have column 'pv_power_kw' (generation in kW).
            
        price_data : list of dict
            List of price dictionaries from ENTSO-E API.
            Each dict must have 'price' key (in EUR/MWh).
            
        Returns:
        --------
        dict
            Dictionary containing:
            - total_revenue_eur: Annual revenue from selling all PV generation (EUR)
            - total_generation_mwh: Total annual PV generation (MWh)
            - weighted_avg_price: Capture price - what solar actually gets (EUR/MWh)
            - overall_avg_price: Baseload price - market average (EUR/MWh)
            - cannibalization_loss_eur_mwh: Price difference per MWh (EUR/MWh)
            - cannibalization_loss_eur_annual: Total annual loss due to profile (EUR)
            - capture_rate: Ratio of capture to baseload price (0-1)
            - hourly_data: DataFrame with hour-by-hour breakdown for charts
            
        Example:
        --------
        >>> result = BaselineService.calculate_pv_baseline(pv_df, prices)
        >>> print(f"Baseline Revenue: €{result['total_revenue_eur']:,.0f}")
        >>> print(f"Capture Rate: {result['capture_rate']:.1%}")
        """
        
        # ===================================================================
        # STEP 1: Prepare Data
        # ===================================================================
        # Create a copy of the PV dataframe to avoid modifying the original
        df = pv_df.copy()
        
        # Convert price_data list to Series with datetime index
        # price_data is expected to be a list of dicts: [{'timestamp': '...', 'price': ...}]
        price_df = pd.DataFrame(price_data)
        if not price_df.empty:
            # Ensure timestamp column is datetime and set as index
            if 'timestamp' in price_df.columns:
                price_df['timestamp'] = pd.to_datetime(price_df['timestamp'], utc=True)
                price_df.set_index('timestamp', inplace=True)
            
            # Merge PV data and Price data on index
            # This ensures we match exactly the same hours
            df = df.join(price_df['price'], how='inner')
        else:
            # Handle empty price data gracefully
            df['price'] = 0.0
        
        # Check if we have data after merge
        if df.empty:
            raise ValueError("No overlapping data found between PV generation and Prices. Please check date ranges.")

        # ===================================================================
        # STEP 2: Calculate Revenue
        # ===================================================================
        # Formula: Revenue (EUR) = Generation (MW) × Price (EUR/MWh) × Time (h)
        # Since we have hourly data and generation in kW, we convert:
        # Revenue = (kW / 1000) × EUR/MWh × 1 hour
        df['revenue_eur'] = (df['pv_power_kw'] / 1000) * df['price']
        
        # Sum up all hourly revenues to get annual total
        total_revenue = df['revenue_eur'].sum()
        
        # ===================================================================
        # STEP 3: Calculate Generation Totals
        # ===================================================================
        # Convert kW to MWh: Sum all kW values and divide by 1000
        total_generation_mwh = df['pv_power_kw'].sum() / 1000
        
        # ===================================================================
        # STEP 4: Calculate Cannibalization Metrics
        # ===================================================================
        # CAPTURE PRICE (Weighted Average)
        # This is what the solar plant actually receives per MWh
        # Formula: Sum(Generation_t × Price_t) / Sum(Generation_t)
        # We weight each hour's price by how much we generated that hour
        weighted_avg_price = np.average(
            df['price'],
            weights=df['pv_power_kw']  # Higher weight when we generate more
        )
        
        # BASELOAD PRICE (Simple Average)
        # This is what a 24/7 plant would receive
        # Just the arithmetic mean of all hourly prices
        overall_avg_price = df['price'].mean()
        
        # CANNIBALIZATION LOSS (Per MWh)
        # The difference between what we COULD get and what we DO get
        # Positive value = we're losing money due to our generation profile
        cannibalization_loss_eur_mwh = overall_avg_price - weighted_avg_price
        
        # ===================================================================
        # STEP 5: Calculate Annual Impact
        # ===================================================================
        # POTENTIAL REVENUE (if we could sell at baseload price)
        potential_revenue = total_generation_mwh * overall_avg_price
        
        # ACTUAL REVENUE (what we really get)
        actual_revenue = total_revenue
        
        # TOTAL CANNIBALIZATION LOSS (Annual)
        # This is the EUR amount we "lose" per year due to solar's midday profile
        cannibalization_loss_eur_annual = potential_revenue - actual_revenue
        
        # ===================================================================
        # STEP 6: Calculate Capture Rate
        # ===================================================================
        # Capture Rate = Capture Price / Baseload Price
        # Example: 72% means we only capture 72% of the market average price
        # This is a key metric for solar projects
        # Typical values: 70-90% (lower = more cannibalization)
        capture_rate = weighted_avg_price / overall_avg_price if overall_avg_price > 0 else 0
        
        # ===================================================================
        # STEP 7: Identify Hours with Negative Prices
        # ===================================================================
        # Negative prices occur when there's too much renewable generation
        # Without battery, we must either:
        # 1. Sell at negative price (pay to export!)
        # 2. Curtail (waste the energy)
        negative_price_hours = (df['price'] < 0).sum()
        negative_price_revenue_loss = df[df['price'] < 0]['revenue_eur'].sum()
        
        # ===================================================================
        # STEP 8: Calculate Average Revenue per MWh
        # ===================================================================
        # This is useful for comparison with battery scenarios
        avg_revenue_per_mwh = total_revenue / total_generation_mwh if total_generation_mwh > 0 else 0
        
        # ===================================================================
        # STEP 9: Prepare Hourly Data for Charts
        # ===================================================================
        # We'll return the first week of data for visualization
        # This shows the typical daily pattern
        hourly_data = df.head(168)  # 168 hours = 7 days
        
        # ===================================================================
        # RETURN RESULTS
        # ===================================================================
        return {
            # Revenue Metrics
            'total_revenue_eur': round(total_revenue, 2),
            'total_generation_mwh': round(total_generation_mwh, 2),
            'avg_revenue_per_mwh': round(avg_revenue_per_mwh, 2),
            
            # Price Metrics
            'weighted_avg_price': round(weighted_avg_price, 2),
            'overall_avg_price': round(overall_avg_price, 2),
            
            # Cannibalization Metrics
            'cannibalization_loss_eur_mwh': round(cannibalization_loss_eur_mwh, 2),
            'cannibalization_loss_eur_annual': round(cannibalization_loss_eur_annual, 2),
            'capture_rate': round(capture_rate, 4),  # Keep precision for percentage display
            
            # Negative Price Impact
            'negative_price_hours': int(negative_price_hours),
            'negative_price_revenue_loss': round(abs(negative_price_revenue_loss), 2),
            
            # Data for Visualization
            'hourly_data': hourly_data.to_dict(orient='records'),
            
            # Full year data (for potential use in optimization)
            'full_year_df': df
        }
    
    @staticmethod
    def should_recommend_battery(baseline_result, threshold=0.70):
        """
        Determine if battery storage should be recommended based on cannibalization.
        
        The PRD specifies that we should highlight the value of battery when
        the capture rate falls below a certain threshold (default 70%).
        
        Parameters:
        -----------
        baseline_result : dict
            Result dictionary from calculate_pv_baseline()
            
        threshold : float, optional
            Capture rate threshold below which to recommend battery.
            Default is 0.70 (70%) as specified by user.
            
        Returns:
        --------
        dict
            Recommendation details:
            - recommend: bool - Whether to recommend battery
            - reason: str - Human-readable explanation
            - severity: str - 'high', 'medium', 'low'
            
        Example:
        --------
        >>> recommendation = BaselineService.should_recommend_battery(result)
        >>> if recommendation['recommend']:
        >>>     st.warning(recommendation['reason'])
        """
        capture_rate = baseline_result['capture_rate']
        cannibalization_loss = baseline_result['cannibalization_loss_eur_annual']
        negative_price_hours = baseline_result['negative_price_hours']
        
        # Determine if we should recommend battery
        recommend = capture_rate < threshold
        
        # Determine severity
        if capture_rate < 0.60:
            severity = 'high'
        elif capture_rate < 0.70:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Generate explanation
        if recommend:
            reason = f"""
⚠️ **Battery Storage Recommended**

Your capture rate is {capture_rate:.1%}, which means your solar plant only captures {capture_rate:.1%} of the average market price due to solar's midday generation profile.

**Annual Impact:**
- Cannibalization Loss: €{cannibalization_loss:,.0f}/year
- Negative Price Hours: {negative_price_hours} hours/year

**Battery Solution:**
Adding battery storage can recover most of this loss by:
1. Shifting solar generation to high-price hours (arbitrage)
2. Avoiding negative price exposure (curtailment prevention)
3. Capturing additional arbitrage opportunities
            """
        else:
            reason = f"""
✅ **Good Capture Rate**

Your capture rate is {capture_rate:.1%}, which is relatively healthy.
However, battery storage may still provide value through arbitrage 
and negative price mitigation.
            """
        
        return {
            'recommend': recommend,
            'reason': reason.strip(),
            'severity': severity,
            'capture_rate': capture_rate,
            'threshold': threshold
        }


# ===================================================================
# Create singleton instance for easy import
# ===================================================================
baseline_service = BaselineService()
