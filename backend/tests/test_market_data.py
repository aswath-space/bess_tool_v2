
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.entsoe_service import EntsoeService
from app.utils.zone_mapping import get_entsoe_zone

class TestMarketData(unittest.TestCase):
    def setUp(self):
        self.service = EntsoeService()
        # Mock the client to avoid real API calls
        self.service.client = MagicMock()

    def test_zone_mapping(self):
        # Test direct mapping
        self.assertEqual(get_entsoe_zone('DE'), 'DE_LU')
        self.assertEqual(get_entsoe_zone('FR'), 'FR')
        # Test default fallback
        self.assertEqual(get_entsoe_zone('XX'), 'XX')

    @patch('app.services.entsoe_service.Nominatim')
    def test_get_zone_from_lat_lon(self, mock_geolocator):
        # Mock geolocator response
        mock_location = MagicMock()
        mock_location.raw = {'address': {'country_code': 'de'}}
        
        # Setup the mock instance
        mock_geo_instance = MagicMock()
        mock_geo_instance.reverse.return_value = mock_location
        self.service.geolocator = mock_geo_instance

        zone = self.service.get_zone_from_lat_lon(52.52, 13.405)
        self.assertEqual(zone, 'DE_LU')

    def test_fetch_day_ahead_prices(self):
        # Mock API response
        start = pd.Timestamp('2023-01-01', tz='UTC')
        end = pd.Timestamp('2023-01-02', tz='UTC')
        
        # Create a dummy series as returned by entsoe-py
        index = pd.date_range(start=start, end=end, freq='H', inclusive='left')
        data = [50.0] * len(index)
        mock_series = pd.Series(data, index=index, name='price')
        
        self.service.client.query_day_ahead_prices.return_value = mock_series

        # Test fetch
        # We need to patch os.path.exists to avoid reading from cache for this test
        with patch('os.path.exists', return_value=False):
             # And patch to_csv to avoid writing to disk
            with patch('pandas.DataFrame.to_csv'):
                df = self.service.fetch_day_ahead_prices('DE_LU', start, end)
                
                self.assertEqual(len(df), 24)
                self.assertEqual(df.iloc[0]['price'], 50.0)
                self.service.client.query_day_ahead_prices.assert_called_once()

if __name__ == '__main__':
    unittest.main()
