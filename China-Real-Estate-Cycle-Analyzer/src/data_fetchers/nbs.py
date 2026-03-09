"""
National Bureau of Statistics (China) Data Fetcher
API: https://data.stats.gov.cn/
"""

import requests
import pandas as pd
from typing import Optional
from .base import BaseDataFetcher
import logging

logger = logging.getLogger(__name__)


class NBSDataFetcher(BaseDataFetcher):
    """Fetcher for National Bureau of Statistics data"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://data.stats.gov.cn/"
        
    def fetch(self, 
               code: str, 
               start_date: str, 
               end_date: str,
               city: str = "全国") -> pd.DataFrame:
        """
        Fetch data from NBS API
        
        Args:
            code: Statistical code (e.g., 'FD0314A03' for housing sales)
            start_date: Start date (YYYY-MM)
            end_date: End date (YYYY-MM)
            city: City name or "全国" for national
            
        Returns:
            DataFrame with columns: date, value, city
        """
        # Check cache first
        cache_key = f"nbs_{code}_{city}_{start_date}_{end_date}"
        cached = self.load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Note: Actual API requires registration
        # This is a placeholder implementation
        logger.warning("NBS API key not configured, using mock data")
        
        # Generate mock data for demonstration
        dates = pd.date_range(start=start_date, end=end_date, freq='M')
        data = {
            'date': dates,
            'value': [100 + i * 0.5 + (hash(city) % 50) for i in range(len(dates))],
            'city': [city] * len(dates)
        }
        
        df = self.to_dataframe(data)
        self.save_to_cache(df, cache_key)
        
        return df
    
    def get_aci_data(self, city: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get ACI (去化周期) data"""
        # ACI = Inventory / Monthly Sales
        # This is a computed indicator, not directly available from NBS
        # We'll fetch sales and inventory separately
        sales = self.fetch(code='AY0X01', start_date=start_date, end_date=end_date, city=city)
        inventory = self.fetch(code='AY0X02', start_date=start_date, end_date=end_date, city=city)
        
        # Compute ACI
        merged = pd.merge(sales, inventory, on='date', suffixes=('_sales', '_inventory'))
        merged['aci'] = merged['value_inventory'] / merged['value_sales']
        
        return merged[['date', 'aci', 'city']]
    
    def get_housing_sales(self, city: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get housing sales data"""
        return self.fetch(code='AY0X01', start_date=start_date, end_date=end_date, city=city)
    
    def get_housing_inventory(self, city: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get housing inventory data"""
        return self.fetch(code='AY0X02', start_date=start_date, end_date=end_date, city=city)
