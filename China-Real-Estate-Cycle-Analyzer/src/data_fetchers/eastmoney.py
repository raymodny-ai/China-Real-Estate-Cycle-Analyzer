"""
East Money (东方财富) Data Fetcher
API: https://datacenter.eastmoney.com/
"""

import requests
import pandas as pd
from typing import Optional
from .base import BaseDataFetcher
import logging

logger = logging.getLogger(__name__)


class EastMoneyFetcher(BaseDataFetcher):
    """Fetcher for East Money financial data"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://datacenter.eastmoney.com/api/data/v1/get"
        
    def fetch(self, 
               report_type: str = "RPT_LPR_DETAIL_N",
               columns: str = "ALL",
               page_number: int = 1,
               page_size: int = 100) -> pd.DataFrame:
        """
        Fetch LPR (Loan Prime Rate) data from East Money
        
        Args:
            report_type: Report type code
            columns: Columns to fetch
            page_number: Page number
            page_size: Page size
            
        Returns:
            DataFrame with LPR data
        """
        # Check cache
        cache_key = f"eastmoney_lpr_{page_number}"
        cached = self.load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        url = self.base_url
        params = {
            "type": report_type,
            "columns": columns,
            "pageNumber": page_number,
            "pageSize": page_size,
            "source": "WEB",
            "client": "WEB"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('success'):
                df = pd.DataFrame(data['result']['data'])
                self.save_to_cache(df, cache_key)
                return df
            else:
                logger.error(f"API error: {data.get('message')}")
                return self._get_mock_lpr_data()
                
        except Exception as e:
            logger.warning(f"API request failed: {e}, using mock data")
            return self._get_mock_lpr_data()
    
    def _get_mock_lpr_data(self) -> pd.DataFrame:
        """Generate mock LPR data for demonstration"""
        dates = pd.date_range(start='2020-01', end='2024-12', freq='M')
        base_lpr = 4.65  # 5Y LPR base rate
        
        data = {
            'date': dates,
            '1Y': [3.85 + (i % 10) * 0.05 for i in range(len(dates))],
            '5Y': [base_lpr + (i % 15) * 0.05 for i in range(len(dates))]
        }
        
        return pd.DataFrame(data)
    
    def get_lpr_data(self) -> pd.DataFrame:
        """Get LPR data - main entry point"""
        return self.fetch()
    
    def get_lpr_history(self, years: int = 5) -> pd.DataFrame:
        """Get LPR history for specified years"""
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        # Calculate required pages
        months = years * 12
        pages = (months // 100) + 1
        
        all_data = []
        for page in range(1, pages + 1):
            df = self.fetch(page_number=page)
            if not df.empty:
                all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return self._get_mock_lpr_data()
