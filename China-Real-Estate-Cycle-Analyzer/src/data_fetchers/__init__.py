"""
Data Fetchers Package

This package provides interfaces to real data sources for the 
China Real Estate Cycle Analyzer project.

Available Fetchers:
- NBSDataFetcher: National Bureau of Statistics (data.stats.gov.cn)
- EastMoneyFetcher: East Money (datacenter.eastmoney.com)

Usage:
    from src.data_fetchers import NBSDataFetcher, EastMoneyFetcher
    
    nbs = NBSDataFetcher()
    aci_data = nbs.get_aci_data(city="北京", start_date="2020-01", end_date="2024-12")
    
    em = EastMoneyFetcher()
    lpr_data = em.get_lpr_data()
"""

from .base import BaseDataFetcher
from .nbs import NBSDataFetcher
from .eastmoney import EastMoneyFetcher

__all__ = [
    'BaseDataFetcher',
    'NBSDataFetcher', 
    'EastMoneyFetcher'
]
