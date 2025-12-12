import pandas as pd
import openmeteo_requests
import requests_cache
import retry_requests
import pvlib
from fastapi import HTTPException
from datetime import datetime

class PVService:
    def __init__(self):
        # Setup Open-Meteo client with cache and retry
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600, backend='memory')
        retry_session = retry_requests.retry(cache_session, retries=5, backoff_factor=0.2)
        self.client = openmeteo_requests.Client(session=retry_session)

    def fetch_pv_generation(self, lat: float, lon: float, peak_power_kw: float, loss: float, tilt: float, azimuth: float, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches hourly weather data from Open-Meteo (ERA5) and calculates PV output using pvlib.
        Returns a DataFrame with UTC-localized index and 'pv_power_kw'.
        """
        try:
            # 1. Fetch Weather Data (Open-Meteo)
            url = "https://archive-api.open-meteo.com/v1/archive"
            
            # Open-Meteo uses South=0, PVGIS uses South=0. Wait.
            # PVGIS: 0=South, -90=East, 90=West.
            # PVLib: 180=South, 90=East, 270=West. (Standard convention)
            # Correction: PVLib default is 180=South.
            # User input `pv_azimuth`... standard is usually 180=South. 
            # If user inputs 0 for South (common in Europe), we might need to map.
            # Convention check: PRD says "0° (South)". 
            # So if user provides 0, it means South.
            # PVLib expects South=180.
            # Mapping: pvlib_azimuth = input_azimuth + 180.
            
            pvlib_azimuth = azimuth + 180
            
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": ["shortwave_radiation", "direct_normal_irradiance", "diffuse_radiation", "temperature_2m"],
                "timeformat": "unixtime"
            }
            
            print(f"📡 Fetching Open-Meteo data for {start_date} to {end_date} at {lat}, {lon}...")
            responses = self.client.weather_api(url, params=params)
            response = responses[0]
            
            # Process hourly data
            hourly = response.Hourly()
            
            # Construct time range
            start = pd.to_datetime(hourly.Time(), unit="s", utc=True)
            end = pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True)
            interval_seconds = hourly.Interval()
            date_range = pd.date_range(start, end, freq=pd.Timedelta(seconds=interval_seconds), inclusive="left")
            
            # Create DataFrame
            hourly_data = {
                "date": date_range,
                "ghi": hourly.Variables(0).ValuesAsNumpy(),
                "dni": hourly.Variables(1).ValuesAsNumpy(),
                "dhi": hourly.Variables(2).ValuesAsNumpy(),
                "temp_air": hourly.Variables(3).ValuesAsNumpy()
            }
            
            weather_df = pd.DataFrame(data=hourly_data)
            weather_df.set_index("date", inplace=True)
            
            # 2. Physics Simulation (PVLib)
            location = pvlib.location.Location(lat, lon, tz='UTC')
            
            # Calculate Solar Position
            solpos = location.get_solarposition(weather_df.index)
            
            # Calculate POA (Plane of Array) Irradiance
            # Use isotropic model for simplicity, or Hay-Davies
            poa_irradiance = pvlib.irradiance.get_total_irradiance(
                surface_tilt=tilt,
                surface_azimuth=pvlib_azimuth,
                dni=weather_df['dni'],
                ghi=weather_df['ghi'],
                dhi=weather_df['dhi'],
                solar_zenith=solpos['zenith'],
                solar_azimuth=solpos['azimuth']
            )
            
            # Calculate Cell Temperature (using NOCT model or Faiman)
            # Simplified: Cell Temp = Air Temp + (POA * exp / 1000)
            # Using PVWatts model approach implicitly via simple efficiency or manual temp correction
            # Let's use standard PVWatts temperature model
            # Standard parameters for "open rack glass-glass"
            temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']
            cell_temperature = pvlib.temperature.sapm_cell(
                poa_global=poa_irradiance['poa_global'],
                temp_air=weather_df['temp_air'],
                wind_speed=1.0, # Assumed 1 m/s if not fetched
                **temperature_model_parameters
            )
            
            # Calculate DC Power (PVWatts model)
            # peak_power_kw -> nameplate_dc (watts)
            # loss -> total system loss % (so 14% -> 0.86 efficiency factor effectively, but PVWatts has specific loss params)
            # PVWatts `system_loss` parameter expects fraction? No, percent.
            # `gamma_pdc`: Temp coeff of power. -0.004 is roughly -0.4%/C (standard Silicon)
            
            dc_power = pvlib.pvsystem.pvwatts_dc(
                effective_irradiance=poa_irradiance['poa_global'],
                temp_cell=cell_temperature,
                pdc0=peak_power_kw * 1000, # Watts
                gamma_pdc=-0.004,
                temp_ref=25.0
            ) 
            
            # Apply System Losses (Inverter, wiring, soiling, availability)
            # User provided `loss` (e.g. 14%). 
            # dc_power is theoretical DC. output = dc * (1 - loss/100)
            ac_power_watts = dc_power * (1 - loss / 100.0)
            
            # Handle negative values (night)
            ac_power_watts = ac_power_watts.clip(lower=0)
            
            # Return result
            result_df = pd.DataFrame({'pv_power_kw': ac_power_watts / 1000.0}) # Convert to kW
            
            # Resample to hourly mean (Open-Meteo is hour-ending or hour-starting? It returns point timestamps)
            # Usually :00.
            result_df = result_df.resample('h').mean().fillna(0)
            
            return result_df

        except Exception as e:
            # Fallback or Error
            print(f"Open-Meteo Error: {e}")
            raise HTTPException(status_code=500, detail=f"Open-Meteo/PVLib Simulation Error: {str(e)}")

pv_service = PVService()
