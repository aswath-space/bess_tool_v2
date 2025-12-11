import os
import pandas as pd
from datetime import datetime
from backend.app.services.entsoe_service import entsoe_service
from backend.app.services.price_strategy import PriceStrategy

class EntsoeApiStrategy:
    """Strategy to fetch prices from ENTSO-E API."""
    def fetch_prices(self, zone: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
        # Use simple caching wrapper from existing service
        # Existing service returns DataFrame with 'price' column
        return entsoe_service.fetch_day_ahead_prices(zone, start_date, end_date)

class CsvFileStrategy:
    """Strategy to fetch prices from local CSV files."""
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def fetch_prices(self, zone: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
        # Construct path, e.g., prices_COUNTRY_YEAR.csv
        # For simplicity, we'll look for a generic 'dummy_country_data.csv' or similar if zone matches
        file_path = os.path.join(self.data_dir, f"{zone.lower()}_prices.csv")
        
        if not os.path.exists(file_path):
             # Fallback to dummy data
             file_path = os.path.join(self.data_dir, "dummy_country_data.csv")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No data file found for {zone} and no dummy fallback.")
            
        df = pd.read_csv(file_path)
        # Ensure timestamp parsing
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        # Filter by date
        # Handle timezone naive vs aware
        if df.index.tz is None:
             df.index = df.index.tz_localize('UTC')
             
        mask = (df.index >= start_date) & (df.index <= end_date)
        return df.loc[mask]

class MarketDataService:
    def __init__(self):
        # Configuration: Map zones to strategies
        # By default, use ENTSO-E. If zone is in a special list, use CSV.
        self.csv_zones = ['FUTURE_GRID', 'DEMO_LAND']
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'prices')
        
    def get_strategy(self, zone: str) -> PriceStrategy:
        if zone in self.csv_zones:
            return CsvFileStrategy(self.data_dir)
        return EntsoeApiStrategy()

    def get_prices(self, zone: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
        strategy = self.get_strategy(zone)
        return strategy.fetch_prices(zone, start_date, end_date)

market_data_service = MarketDataService()
