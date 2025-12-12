
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
# Try loading from standard .env or user-specified entso.env
load_dotenv() # Defaults
load_dotenv("entso.env") # Overlay with specific file if present

from .services.entsoe_service import entsoe_service
from .services.pv_service import pv_service
from .services.optimization_service import optimization_service
from pydantic import BaseModel


app = FastAPI(title="PV-BESS Investor Guide Tool API")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProjectConfig(BaseModel):
    lat: float
    lon: float
    pv_capacity_mw: float
    pv_tilt: float
    pv_azimuth: float
    bess_capacity_mwh: float
    bess_power_mw: float
    loss_factor: float = 14.0
    # Optimization parameters (optional with defaults)
    min_soc_percent: float = 0.05
    throughput_cost_eur_mwh: float = 10.0

@app.get("/")
def read_root():
    return {"message": "PV-BESS Investor Guide Tool Backend is running"}

@app.get("/api/market-data")
def get_market_data(
    lat: float, 
    lon: float, 
    start_date: str = Query(None, description="Start date in YYYY-MM-DD format. Defaults to 1 year ago.")
):
    """
    Fetches Day-Ahead Market prices for the location.
    If start_date is not provided, fetches the last 365 days.
    """
    # 1. Determine Zone
    zone = entsoe_service.get_zone_from_lat_lon(lat, lon)
    if not zone:
        raise HTTPException(status_code=404, detail="Could not determine ENTSO-E zone for this location.")

    # 2. Determine Date Range
    if start_date:
        try:
            start = pd.Timestamp(start_date, tz='UTC')
            end = start + pd.Timedelta(days=365) # Default to 1 year duration if start is given
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        # Default: Last 365 days ending yesterday (to ensure full day data)
        end = pd.Timestamp.now(tz='UTC').normalize()
        start = end - pd.Timedelta(days=365)

    # 3. Fetch Data
    try:
        df = entsoe_service.fetch_day_ahead_prices(zone, start, end)
        
        # Format for JSON response
        # Resample to hourly if needed, fill NaNs, etc.
        # Returning a list of records: [{"timestamp": "...", "price": ...}, ...]
        result = df.reset_index().rename(columns={'index': 'timestamp', 'price': 'price'})
        result['timestamp'] = result['timestamp'].dt.isoformat()
        
        return {
            "zone": zone,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "data": result.to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize")
def run_optimization(config: ProjectConfig):
    try:
        # 1. Determine Analysis Period (Last Complete 12 Months)
        # We need a shared consistent year.
        today = pd.Timestamp.now(tz='UTC')
        start_of_current_month = today.replace(day=1).normalize()
        end = start_of_current_month - pd.Timedelta(seconds=1)
        start = start_of_current_month - pd.DateOffset(years=1)
        
        simulation_year = start.year
        
        zone = entsoe_service.get_zone_from_lat_lon(config.lat, config.lon)
        if not zone:
             # Fallback
             zone = "DE_LU" # Assume German zone if mapping fails? Or error.
             print("Warning: Could not determine zone. Falling back to DE_LU.")
             
        prices_df = entsoe_service.fetch_day_ahead_prices(zone, start, end)
        
        # Convert to list of dicts for service
        price_data = prices_df.reset_index().rename(columns={'index': 'timestamp', 'price': 'price'}).to_dict(orient='records')
        
        # 2. Fetch PV Data (Hourly simulation for ALIGNED year)
        # PVGIS seriescalc
        pv_df = pv_service.fetch_pv_generation(
            lat=config.lat,
            lon=config.lon,
            peak_power_kw=config.pv_capacity_mw * 1000,
            loss=config.loss_factor,
            tilt=config.pv_tilt,
            azimuth=config.pv_azimuth,
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.strftime('%Y-%m-%d')
        )
        
        # 3. Run Optimization (MILP)
        result = optimization_service.run_optimization(
            pv_df=pv_df,
            price_data=price_data,
            bess_power_mw=config.bess_power_mw,
            bess_capacity_mwh=config.bess_capacity_mwh,
            min_soc_percent=config.min_soc_percent,
            throughput_cost_eur_mwh=config.throughput_cost_eur_mwh
        )
        
        # Attach zone info for UI context
        result['zone'] = zone
        result['simulation_year'] = simulation_year
        
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
