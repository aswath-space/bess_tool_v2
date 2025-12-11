"""
Unit Tests for Auto-Sizing Service
===================================

Tests for battery sizing recommendations.
"""

import pytest
from backend.app.services.auto_sizing_service import auto_sizing_service


class TestAutoSizingService:
    """Test suite for auto-sizing service."""
    
    def test_smart_defaults_structure(self):
        """Test that smart defaults return expected structure."""
        result = auto_sizing_service.calculate_smart_defaults(
            pv_capacity_mw=10.0,
            mode='moderate'
        )
        
        assert 'power_mw' in result
        assert 'capacity_mwh' in result
        assert 'duration_hours' in result
        assert 'power_ratio' in result
        assert 'rationale' in result
        
        # Values should be reasonable
        assert result['power_mw'] > 0
        assert result['capacity_mwh'] > 0
        assert result['duration_hours'] > 0
    
    def test_moderate_sizing(self):
        """Test moderate sizing mode (40% of PV, 4-hour duration)."""
        pv_capacity = 10.0
        result = auto_sizing_service.calculate_smart_defaults(
            pv_capacity_mw=pv_capacity,
            mode='moderate'
        )
        
        # Should be 40% of PV capacity
        expected_power = pv_capacity * 0.4
        assert abs(result['power_mw'] - expected_power) < 0.01
        
        # Should be 4-hour duration
        assert result['duration_hours'] == 4
        
        # Capacity = Power × Duration
        expected_capacity = expected_power * 4
        assert abs(result['capacity_mwh'] - expected_capacity) < 0.01
    
    def test_conservative_sizing(self):
        """Test conservative sizing mode (25% of PV, 2-hour duration)."""
        pv_capacity = 10.0
        result = auto_sizing_service.calculate_smart_defaults(
            pv_capacity_mw=pv_capacity,
            mode='conservative'
        )
        
        # Should be 25% of PV capacity
        expected_power = pv_capacity * 0.25
        assert abs(result['power_mw'] - expected_power) < 0.01
        
        # Should be 2-hour duration
        assert result['duration_hours'] == 2
    
    def test_aggressive_sizing(self):
        """Test aggressive sizing mode (60% of PV, 6-hour duration)."""
        pv_capacity = 10.0
        result = auto_sizing_service.calculate_smart_defaults(
            pv_capacity_mw=pv_capacity,
            mode='aggressive'
        )
        
        # Should be 60% of PV capacity
        expected_power = pv_capacity * 0.6
        assert abs(result['power_mw'] - expected_power) < 0.01
        
        # Should be 6-hour duration
        assert result['duration_hours'] == 6
    
    def test_all_sizing_options(self):
        """Test getting all sizing options at once."""
        result = auto_sizing_service.get_all_sizing_options(pv_capacity_mw=10.0)
        
        assert 'conservative' in result
        assert 'moderate' in result
        assert 'aggressive' in result
        
        # Conservative should be smallest
        assert result['conservative']['power_mw'] < result['moderate']['power_mw']
        assert result['moderate']['power_mw'] < result['aggressive']['power_mw']
    
    def test_validation_reasonable_sizing(self):
        """Test validation with reasonable battery sizing."""
        validation = auto_sizing_service.validate_battery_sizing(
            power_mw=4.0,
            capacity_mwh=16.0,
            pv_capacity_mw=10.0
        )
        
        # Should have no warnings for reasonable sizing
        assert validation['has_warnings'] == False
        assert len(validation['warnings']) == 0
    
    def test_validation_oversized_power(self):
        """Test validation warning for oversized power."""
        validation = auto_sizing_service.validate_battery_sizing(
            power_mw=15.0,  # 150% of PV - very high
            capacity_mwh=60.0,
            pv_capacity_mw=10.0
        )
        
        # Should warn about oversized power
        assert validation['has_warnings'] == True
        assert any('power' in w.lower() for w in validation['warnings'])
    
    def test_validation_short_duration(self):
        """Test validation warning for very short duration."""
        validation = auto_sizing_service.validate_battery_sizing(
            power_mw=10.0,
            capacity_mwh=5.0,  # 0.5 hour duration
            pv_capacity_mw=10.0
        )
        
        # Should warn about short duration
        assert validation['has_warnings'] == True
        assert any('duration' in w.lower() for w in validation['warnings'])
    
    def test_validation_long_duration(self):
        """Test validation warning for very long duration."""
        validation = auto_sizing_service.validate_battery_sizing(
            power_mw=2.0,
            capacity_mwh=20.0,  # 10 hour duration
            pv_capacity_mw=10.0
        )
        
        # Should warn about long duration
        assert validation['has_warnings'] == True
        assert any('duration' in w.lower() for w in validation['warnings'])
    
    def test_small_pv_system(self):
        """Test sizing for small PV system (1 MW)."""
        result = auto_sizing_service.calculate_smart_defaults(
            pv_capacity_mw=1.0,
            mode='moderate'
        )
        
        # Should still provide reasonable sizing
        assert result['power_mw'] == 0.4
        assert result['capacity_mwh'] == 1.6
        assert result['duration_hours'] == 4
    
    def test_large_pv_system(self):
        """Test sizing for large PV system (100 MW)."""
        result = auto_sizing_service.calculate_smart_defaults(
            pv_capacity_mw=100.0,
            mode='moderate'
        )
        
        # Should scale linearly
        assert result['power_mw'] == 40.0
        assert result['capacity_mwh'] == 160.0
        assert result['duration_hours'] == 4


class TestAutoSizingEdgeCases:
    """Test edge cases for auto-sizing."""
    
    def test_invalid_mode(self):
        """Test handling of invalid sizing mode."""
        try:
            result = auto_sizing_service.calculate_smart_defaults(
                pv_capacity_mw=10.0,
                mode='invalid_mode'
            )
            # Should either default to moderate or raise error
            assert result is not None
        except (ValueError, KeyError):
            # It's acceptable to raise an error for invalid mode
            pass
    
    def test_zero_pv_capacity(self):
        """Test with zero PV capacity."""
        # This edge case might raise an error or return zero
        try:
            result = auto_sizing_service.calculate_smart_defaults(
                pv_capacity_mw=0.0,
                mode='moderate'
            )
            # If it succeeds, battery should be zero
            assert result['power_mw'] == 0.0
        except (ValueError, ZeroDivisionError):
            # It's acceptable to raise an error
            pass
    
    def test_validation_zero_power(self):
        """Test validation with zero power."""
        validation = auto_sizing_service.validate_battery_sizing(
            power_mw=0.0,
            capacity_mwh=10.0,
            pv_capacity_mw=10.0
        )
        
        # Should have warnings
        assert validation['has_warnings'] == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
