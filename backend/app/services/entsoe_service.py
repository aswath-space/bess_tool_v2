
import os
import pandas as pd
from datetime import datetime, timedelta
from entsoe import EntsoePandasClient
from geopy.geocoders import Nominatim
from app.utils.zone_mapping import get_entsoe_zone

# Ensure cache directory exists
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

class EntsoeService:
    def __init__(self):
        api_key = os.getenv('ENTSOE_API_KEY')
        if not api_key:
            raise ValueError(
                "❌ ENTSO-E API Key not found!\n\n"
                "For Streamlit Cloud:\n"
                "1. Go to your app settings\n"
                "2. Click 'Secrets'\n"
                "3. Add: [entsoe]\n"
                "        api_key = 'your-key-here'\n\n"
                "For local development:\n"
                "1. Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml\n"
                "2. Add your API key\n\n"
                "Get your API key at: https://transparency.entsoe.eu/\n"
                "(Register → Account Settings → Web API Security Token)"
            )
        
        self.client = EntsoePandasClient(api_key=api_key)
        self.geolocator = Nominatim(user_agent="pv_bess_investor_guide_tool")

    def get_zone_from_lat_lon(self, lat: float, lon: float) -> str:
        """
        Reverse geocodes the coordinates to find the country and maps it to an ENTSO-E zone.
        """
        try:
            location = self.geolocator.reverse((lat, lon), language='en')
            if location and 'address' in location.raw:
                country_code = location.raw['address'].get('country_code')
                if country_code:
                    return get_entsoe_zone(country_code)
            return None
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None

    def fetch_day_ahead_prices(self, zone: str, start_date: pd.Timestamp, end_date: pd.Timestamp):
        """
        Fetches Day-Ahead Market prices for the given zone and date range.
        Fallback order:
        1. Local cache (recent API fetches)
        2. ENTSO-E API (if available)
        3. Manual uploads (backend/data/prices/{zone}.csv)
        4. Fallback data (backend/data/prices/fallback.csv)
        """
        cache_file = os.path.join(CACHE_DIR, f"dam_prices_{zone}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv")
        
        # Try cache first
        if os.path.exists(cache_file):
            print(f"✓ Loading from cache: {cache_file}")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
        
        # Try ENTSO-E API
        if self.client:
            print(f"📡 Fetching from ENTSO-E API for {zone}...")
            try:
                prices_series = self.client.query_day_ahead_prices(country_code=zone, start=start_date, end=end_date)
                df = prices_series.to_frame(name='price')
                
                # Save to cache for future use
                df.to_csv(cache_file)
                print(f"✓ Data cached successfully")
                return df
            except Exception as e:
                print(f"⚠️ ENTSO-E API failed: {e}")
                print(f"Falling back to manual data...")
        
        # Try manual upload for specific zone
        manual_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'prices', f'{zone}.csv'
        )
        
        if os.path.exists(manual_file):
            print(f"✓ Loading manual data: {manual_file}")
            df = pd.read_csv(manual_file, index_col=0, parse_dates=True)
            # Filter to requested date range
            df = df.loc[start_date:end_date]
            return df
        
        # Try global fallback
        fallback_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'prices', 'fallback.csv'
        )
        
        if os.path.exists(fallback_file):
            print(f"⚠️ Using fallback data: {fallback_file}")
            df = pd.read_csv(fallback_file, index_col=0, parse_dates=True)
            df = df.loc[start_date:end_date]
            return df
        
        # No data available
        raise ValueError(
            f"❌ No price data available for {zone}\n\n"
            f"Options to fix:\n"
            f"1. Check your ENTSO-E API key\n"
            f"2. Upload manual CSV to: backend/data/prices/{zone}.csv\n"
            f"3. Upload fallback CSV to: backend/data/prices/fallback.csv\n\n"
            f"CSV format: timestamp (index), price (column)"
        )

entsoe_service = EntsoeService()

