
import pytest
import pandas as pd
import sys
import os

# Set dummy API key BEFORE importing app (though not needed for PVService, good practice)
os.environ['ENTSOE_API_KEY'] = 'dummy_key'

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend'))

from app.services.pv_service import pv_service

def test_fetch_pv_generation_open_meteo():
    """Verify Open-Meteo fetching and PVLib calculation for 2024."""
    print("\nTesting Open-Meteo for Berlin (2024)...")
    
    try:
        df = pv_service.fetch_pv_generation(
            lat=52.52,
            lon=13.405,
            peak_power_kw=10.0,
            loss=14.0,
            tilt=35.0,
            azimuth=0.0, # 0=South (PVGIS convention), maps to 180 in service
            year=2024
        )
        
        print(f"Result shape: {df.shape}")
        print(df.head())
        print(df.describe())
        
        # Checks
        assert not df.empty, "DataFrame should not be empty"
        assert 'pv_power_kw' in df.columns, "Column pv_power_kw missing"
        assert isinstance(df.index, pd.DatetimeIndex), "Index must be DatetimeIndex"
        assert str(df.index.tz) == 'UTC', "Index must be UTC"
        
        # Value checks
        max_power = df['pv_power_kw'].max()
        print(f"Max Power: {max_power} kW")
        assert max_power > 0, "Max power should be positive"
        assert max_power <= 12.0, "Max power shouldn't excessively exceed peak capacity (10kW)" # Allow some over-irradiance
        
        print("✅ Open-Meteo Test Passed!")
        
    except Exception as e:
        pytest.fail(f"Test failed with error: {e}")

if __name__ == "__main__":
    # Allow running directly
    try:
        test_fetch_pv_generation_open_meteo()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
