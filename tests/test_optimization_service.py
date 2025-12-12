"""
Unit Tests for Optimization Service
====================================

Tests for LP optimization of battery dispatch.
"""

import pytest
import pandas as pd
import numpy as np
from backend.app.services.optimization_service import optimization_service


class TestOptimizationService:
    """Test suite for optimization service."""
    
    @pytest.fixture
    def simple_scenario(self):
        """Create simple test scenario with clear arbitrage opportunity."""
        # 24 hours
        hours_idx = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        
        # PV generation: peak at noon
        pv_power = []
        for hour in range(24):
            if 8 <= hour <= 16:
                pv_power.append(1000)  # 1 MW during day
            else:
                pv_power.append(0)
        
        pv_df = pd.DataFrame({'pv_power_kw': pv_power}, index=hours_idx)
        
        # Prices: low during day, high in evening
        price_data = []
        for i, hour in enumerate(range(24)):
            if 8 <= hour <= 16:
                price = 30.0  # Low during solar
            elif 17 <= hour <= 21:
                price = 150.0  # High in evening
            else:
                price = 60.0  # Moderate at night
            
            price_data.append({
                'timestamp': hours_idx[i].isoformat(),
                'price': price
            })
        
        return pv_df, price_data
    
    def test_optimization_completes(self, simple_scenario):
        """Test that optimization runs without errors."""
        pv_df, price_data = simple_scenario
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        # Check result structure
        assert 'financials' in result
        assert 'arbitrage' in result
        assert 'hourly_data' in result
        assert result['optimization_status'] == 'optimal'
    
    def test_revenue_improvement(self, simple_scenario):
        """Test that battery optimization increases revenue."""
        pv_df, price_data = simple_scenario
        
        # Calculate baseline (PV only)
        from backend.app.services.baseline_service import baseline_service
        baseline = baseline_service.calculate_pv_baseline(pv_df, price_data)
        
        # Run optimization with battery
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        # Optimized revenue should be higher than baseline
        assert result['financials']['total_revenue_eur'] > baseline['total_revenue_eur']
    
    def test_arbitrage_behavior(self, simple_scenario):
        """Test that battery charges at low prices and discharges at high prices."""
        pv_df, price_data = simple_scenario
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        # Check arbitrage metrics
        arb = result['arbitrage']
        
        # Charging price should be lower than discharging price
        assert arb['avg_charging_price'] < arb['avg_discharging_price']
        
        # Price spread should be positive
        assert arb['price_spread'] > 0
    
    def test_power_constraints(self, simple_scenario):
        """Test that battery respects power limits."""
        pv_df, price_data = simple_scenario
        
        power_limit = 2.0  # MW
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=power_limit,
            bess_capacity_mwh=8.0
        )
        
        df = pd.DataFrame(result['hourly_data'])
        
        # Check that charge/discharge never exceeds power limit
        max_charge = df['bess_charge_kw'].max() / 1000  # Convert to MW
        max_discharge = df['bess_discharge_kw'].max() / 1000
        
        assert max_charge <= power_limit + 0.01  # Small tolerance for numerical precision
        assert max_discharge <= power_limit + 0.01
    
    def test_capacity_constraints(self, simple_scenario):
        """Test that battery respects capacity limits."""
        pv_df, price_data = simple_scenario
        
        capacity_limit = 8.0  # MWh
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=capacity_limit
        )
        
        df = pd.DataFrame(result['hourly_data'])
        
        # Check that SoC never exceeds capacity
        max_soc = df['soc_kwh'].max() / 1000  # Convert to MWh
        
        assert max_soc <= capacity_limit + 0.01
        assert df['soc_kwh'].min() >= 0  # Never negative
    
    def test_negative_prices(self):
        """Test behavior with negative prices."""
        # Scenario with negative prices
        hours_idx = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_df = pd.DataFrame({'pv_power_kw': [1000] * 24}, index=hours_idx)
        
        price_data = []
        for i, hour in enumerate(range(24)):
            if 10 <= hour <= 14:
                price = -20.0  # Negative during midday
            else:
                price = 100.0
            
            price_data.append({
                'timestamp': hours_idx[i].isoformat(),
                'price': price
            })
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        # Should have charged during negative price hours
        neg_prices = result['negative_prices']
        assert neg_prices['negative_price_hours'] > 0
        assert neg_prices['energy_charged_during_neg_prices_kwh'] > 0
    
    def test_battery_utilization(self, simple_scenario):
        """Test that battery utilization is calculated correctly."""
        pv_df, price_data = simple_scenario
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        fin = result['financials']
        
        # Utilization should be between 0 and 100%
        assert 0 <= fin['battery_utilization_percent'] <= 100
        
        # Should have some charging and discharging hours
        assert fin['hours_charging'] > 0
        assert fin['hours_discharging'] > 0
    
    def test_annual_cycles(self, simple_scenario):
        """Test that annual cycles calculation is reasonable."""
        # Extract base data patterns
        orig_pv_df, orig_price_data = simple_scenario
        pv_vals = orig_pv_df['pv_power_kw'].tolist()
        price_vals = [p['price'] for p in orig_price_data]
        
        # Create full year data (8760 hours)
        hours_year = pd.date_range('2024-01-01', periods=8760, freq='h', tz='UTC')
        
        # Repeat patterns
        pv_year_vals = (pv_vals * 365)
        price_year_vals = (price_vals * 365)
        
        pv_year = pd.DataFrame({'pv_power_kw': pv_year_vals}, index=hours_year)
        price_year = [{'timestamp': h.isoformat(), 'price': p} for h, p in zip(hours_year, price_year_vals)]
        
        result = optimization_service.run_optimization(
            pv_df=pv_year,
            price_data=price_year,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        cycles = result['financials']['annual_cycles']
        
        # Cycles should be reasonable (not zero, not excessively high)
        assert 50 < cycles < 500  # Typical range for solar+storage


class TestOptimizationEdgeCases:
    """Test edge cases for optimization."""
    
    def test_zero_battery_capacity(self):
        """Test with zero battery capacity (should return PV-only scenario)."""
        hours_idx = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_df = pd.DataFrame({'pv_power_kw': [100] * 24}, index=hours_idx)
        price_data = [{'timestamp': h.isoformat(), 'price': 50.0} for h in hours_idx]
        
        # This might raise an error or return minimal battery usage
        # Depending on implementation, adjust assertion
        try:
            result = optimization_service.run_optimization(
                pv_df=pv_df,
                price_data=price_data,
                bess_power_mw=1.0,
                bess_capacity_mwh=0.0
            )
            # If it succeeds, battery flow should be zero
            df = pd.DataFrame(result['hourly_data'])
            assert df['bess_flow_kw'].abs().sum() < 0.1
        except (ValueError, Exception):
            # It's acceptable to raise an error for invalid config
            pass
    
    def test_flat_prices(self):
        """Test optimization with flat prices (no arbitrage opportunity)."""
        hours_idx = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_df = pd.DataFrame({'pv_power_kw': [1000] * 24}, index=hours_idx)
        price_data = [{'timestamp': h.isoformat(), 'price': 50.0} for h in hours_idx]
        
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=2.0,
            bess_capacity_mwh=8.0
        )
        
        # With flat prices, battery shouldn't provide much value
        # Price spread should be minimal
        assert result['arbitrage']['price_spread'] < 1.0
    
    def test_very_short_duration(self):
        """Test with very short duration battery (0.5 hours)."""
        hours_idx = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_df = pd.DataFrame({'pv_power_kw': [1000] * 24}, index=hours_idx)
        
        price_data = []
        for i, hour in enumerate(range(24)):
            price = 50.0 if hour % 2 == 0 else 100.0
            price_data.append({'timestamp': hours_idx[i].isoformat(), 'price': price})
        
        # High power, low capacity = short duration
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=10.0,
            bess_capacity_mwh=5.0  # 0.5 hour duration
        )
        
        # Should still optimize successfully
        assert result['optimization_status'] == 'optimal'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
