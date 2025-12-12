"""
Unit Tests for Baseline Service
================================

Tests for PV baseline revenue and cannibalization calculations.
"""

import pytest
import pandas as pd
import numpy as np
from backend.app.services.baseline_service import baseline_service


class TestBaselineService:
    """Test suite for baseline service calculations."""
    
    @pytest.fixture
    def sample_pv_data(self):
        """Create sample PV generation data."""
        # 24 hours of sample data
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_power = []
        
        # Simulate solar generation pattern (peak at noon)
        for hour in range(24):
            if 6 <= hour <= 18:
                # Solar generation during daylight hours
                pv_power.append(np.sin((hour - 6) * np.pi / 12) * 1000)  # kW
            else:
                pv_power.append(0)
        
        df = pd.DataFrame({
            'pv_power_kw': pv_power
        }, index=hours)
        return df
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data."""
        # 24 hours of sample prices
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        prices = []
        for i, hour in enumerate(range(24)):
            if 10 <= hour <= 16:
                price = 50.0
            elif 17 <= hour <= 21:
                price = 120.0
            else:
                price = 80.0
            
            prices.append({
                'timestamp': hours[i].isoformat(),
                'price': price
            })
        
        return prices
    
    def test_calculate_pv_baseline_basic(self, sample_pv_data, sample_price_data):
        """Test basic baseline calculation returns expected structure."""
        result = baseline_service.calculate_pv_baseline(
            pv_df=sample_pv_data,
            price_data=sample_price_data
        )
        
        # Check that all expected keys are present
        assert 'total_revenue_eur' in result
        assert 'total_generation_mwh' in result
        assert 'weighted_avg_price' in result
        assert 'overall_avg_price' in result
        assert 'capture_rate' in result
        assert 'cannibalization_loss_eur_mwh' in result
        
        # Check that values are reasonable
        assert result['total_revenue_eur'] > 0
        assert result['total_generation_mwh'] > 0
        assert 0 < result['capture_rate'] <= 1
    
    def test_capture_rate_calculation(self, sample_pv_data, sample_price_data):
        """Test that capture rate reflects cannibalization effect."""
        result = baseline_service.calculate_pv_baseline(
            pv_df=sample_pv_data,
            price_data=sample_price_data
        )
        
        # Capture rate should be less than 1 due to cannibalization
        # (solar generates most during low-price hours)
        assert result['capture_rate'] < 1.0
        
        # Weighted average price should be less than overall average
        assert result['weighted_avg_price'] < result['overall_avg_price']
        
        # Cannibalization loss should be positive
        assert result['cannibalization_loss_eur_mwh'] > 0
    
    def test_zero_generation(self):
        """Test handling of zero generation."""
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_data = pd.DataFrame({
            'pv_power_kw': [0] * 24
        }, index=hours)
        
        price_data = [{'timestamp': h.isoformat(), 'price': 50.0} for h in hours]
        
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        
        # Revenue should be zero
        assert result['total_revenue_eur'] == 0
        assert result['total_generation_mwh'] == 0
    
    def test_negative_prices(self):
        """Test handling of negative prices."""
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_data = pd.DataFrame({
            'pv_power_kw': [1000] * 24  # Constant generation
        }, index=hours)
        
        # Some negative prices
        prices_vals = [-10.0] * 12 + [100.0] * 12
        price_data = [{'timestamp': h.isoformat(), 'price': p} for h, p in zip(hours, prices_vals)]
        
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        
        # Should track negative price hours
        assert result['negative_price_hours'] == 12
        assert result['negative_price_revenue_loss'] > 0
    
    def test_battery_recommendation_low_capture_rate(self):
        """Test battery recommendation for low capture rate."""
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        # Create scenario with low capture rate
        pv_vals = [0]*6 + [1000]*12 + [0]*6
        pv_data = pd.DataFrame({
            'pv_power_kw': pv_vals
        }, index=hours)
        
        # Low prices during solar hours, high at night
        price_vals = [30.0]*6 + [20.0]*12 + [120.0]*6
        price_data = [{'timestamp': h.isoformat(), 'price': p} for h, p in zip(hours, price_vals)]
        
        baseline_result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        recommendation = baseline_service.should_recommend_battery(baseline_result)
        
        # Should recommend battery due to low capture rate
        assert recommendation['recommend'] == True
        assert recommendation['severity'] in ['high', 'medium']
    
    def test_battery_recommendation_good_capture_rate(self):
        """Test battery recommendation for good capture rate."""
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        # Create scenario with good capture rate (flat prices)
        pv_vals = [0]*6 + [1000]*12 + [0]*6
        pv_data = pd.DataFrame({
            'pv_power_kw': pv_vals
        }, index=hours)
        
        # Relatively flat prices
        price_data = [{'timestamp': h.isoformat(), 'price': 80.0} for h in hours]
        
        baseline_result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        recommendation = baseline_service.should_recommend_battery(baseline_result)
        
        # May or may not recommend, but capture rate should be healthy
        assert baseline_result['capture_rate'] > 0.85


class TestBaselineServiceEdgeCases:
    """Test edge cases and error handling."""
    

    def test_mismatched_data_ranges(self):
        """Test handling when PV data and price data have non-overlapping ranges (should raise error)."""
        hours_pv = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        pv_data = pd.DataFrame({
            'pv_power_kw': [100] * 24
        }, index=hours_pv)
        
        # Prices for different day
        hours_prices = pd.date_range('2025-01-01', periods=24, freq='h', tz='UTC')
        price_data = [{'timestamp': h.isoformat(), 'price': 50.0} for h in hours_prices]
        
        # Should raise ValueError due to empty intersection
        with pytest.raises(ValueError, match="No overlapping data found"):
            baseline_service.calculate_pv_baseline(pv_data, price_data)
    
    def test_very_high_cannibalization(self):
        """Test extreme cannibalization scenario."""
        hours = pd.date_range('2024-01-01', periods=24, freq='h', tz='UTC')
        # All generation during lowest price hours
        pv_vals = [1000]*12 + [0]*12
        pv_data = pd.DataFrame({
            'pv_power_kw': pv_vals
        }, index=hours)
        
        # Extremely low prices when solar generates
        price_vals = [1.0]*12 + [200.0]*12
        price_data = [{'timestamp': h.isoformat(), 'price': p} for h, p in zip(hours, price_vals)]
        
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        
        # Capture rate should be very low
        assert result['capture_rate'] < 0.3
        # Cannibalization loss should be very high
        assert result['cannibalization_loss_eur_mwh'] > 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
