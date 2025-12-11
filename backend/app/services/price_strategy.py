from typing import Protocol, List, Dict
import pandas as pd

class PriceStrategy(Protocol):
    def fetch_prices(self, zone: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
        """
        Fetches price data for a given zone/country and date range.
        Returns a DataFrame with at least a 'price' column.
        """
        ...
