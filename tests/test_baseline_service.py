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
        hours = pd.date_range('2024-01-01', periods=24, freq='H')
        pv_power = []
        
        # Simulate solar generation pattern (peak at noon)
        for hour in range(24):
            if 6 <= hour <= 18:
                # Solar generation during daylight hours
                pv_power.append(np.sin((hour - 6) * np.pi / 12) * 1000)  # kW
            else:
                pv_power.append(0)
        
        return pd.DataFrame({
            'time': hours,
            'pv_power_kw': pv_power
        })
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data."""
        # 24 hours of sample prices with lower prices during solar hours
        prices = []
        for hour in range(24):
            if 10 <= hour <= 16:
                # Lower prices during solar peak (cannibalization effect)
                prices.append({'price': 50.0 + np.random.uniform(-5, 5)})
            elif 17 <= hour <= 21:
                # Higher prices in evening
                prices.append({'price': 120.0 + np.random.uniform(-10, 10)})
            else:
                # Moderate prices at night
                prices.append({'price': 80.0 + np.random.uniform(-5, 5)})
        
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
        pv_data = pd.DataFrame({
            'pv_power_kw': [0] * 24
        })
        price_data = [{'price': 50.0}] * 24
        
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        
        # Revenue should be zero
        assert result['total_revenue_eur'] == 0
        assert result['total_generation_mwh'] == 0
    
    def test_negative_prices(self):
        """Test handling of negative prices."""
        pv_data = pd.DataFrame({
            'pv_power_kw': [1000] * 24  # Constant generation
        })
        # Some negative prices
        price_data = [{'price': -10.0}] * 12 + [{'price': 100.0}] * 12
        
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        
        # Should track negative price hours
        assert result['negative_price_hours'] == 12
        assert result['negative_price_revenue_loss'] > 0
    
    def test_battery_recommendation_low_capture_rate(self):
        """Test battery recommendation for low capture rate."""
        # Create scenario with low capture rate
        pv_data = pd.DataFrame({
            'pv_power_kw': [0]*6 + [1000]*12 + [0]*6  # Solar only during day
        })
        # Low prices during solar hours, high at night
        price_data = ([{'price': 30.0}] * 6 + 
                      [{'price': 20.0}] * 12 +  # Low during solar
                      [{'price': 120.0}] * 6)
        
        baseline_result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        recommendation = baseline_service.should_recommend_battery(baseline_result)
        
        # Should recommend battery due to low capture rate
        assert recommendation['recommend'] == True
        assert recommendation['severity'] in ['high', 'medium']
    
    def test_battery_recommendation_good_capture_rate(self):
        """Test battery recommendation for good capture rate."""
        # Create scenario with good capture rate (flat prices)
        pv_data = pd.DataFrame({
            'pv_power_kw': [0]*6 + [1000]*12 + [0]*6
        })
        # Relatively flat prices
        price_data = [{'price': 80.0 + np.random.uniform(-5, 5)}] * 24
        
        baseline_result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        recommendation = baseline_service.should_recommend_battery(baseline_result)
        
        # May or may not recommend, but capture rate should be healthy
        assert baseline_result['capture_rate'] > 0.85


class TestBaselineServiceEdgeCases:
    """Test edge cases and error handling."""
    
    def test_mismatched_data_lengths(self):
        """Test handling when PV data and price data have different lengths."""
        pv_data = pd.DataFrame({
            'pv_power_kw': [100] * 100
        })
        price_data = [{'price': 50.0}] * 50  # Fewer price points
        
        # Should not crash, uses minimum length
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        assert result is not None
    
    def test_very_high_cannibalization(self):
        """Test extreme cannibalization scenario."""
        # All generation during lowest price hours
        pv_data = pd.DataFrame({
            'pv_power_kw': [1000]*12 + [0]*12
        })
        # Extremely low prices when solar generates
        price_data = ([{'price': 1.0}] * 12 + 
                      [{'price': 200.0}] * 12)
        
        result = baseline_service.calculate_pv_baseline(pv_data, price_data)
        
        # Capture rate should be very low
        assert result['capture_rate'] < 0.3
        # Cannibalization loss should be very high
        assert result['cannibalization_loss_eur_mwh'] > 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
