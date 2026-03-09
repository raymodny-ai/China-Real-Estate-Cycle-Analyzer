"""
Base class for data fetchers
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BaseDataFetcher(ABC):
    """Base class for all data fetchers"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = None
        
    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        """Fetch data - must be implemented by subclass"""
        pass
    
    def validate_date_range(self, start_date: str, end_date: str) -> bool:
        """Validate date range format"""
        # Simple validation - can be enhanced
        return len(start_date) == 7 and len(end_date) == 7
    
    def to_dataframe(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Convert dictionary to DataFrame"""
        return pd.DataFrame(data)
    
    def save_to_cache(self, df: pd.DataFrame, filename: str):
        """Save fetched data to cache"""
        cache_dir = Path(__file__).parent.parent / "data" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        filepath = cache_dir / f"{filename}.parquet"
        df.to_parquet(filepath)
        logger.info(f"Data cached to {filepath}")
        
    def load_from_cache(self, filename: str) -> Optional[pd.DataFrame]:
        """Load data from cache"""
        cache_dir = Path(__file__).parent.parent / "data" / "cache"
        filepath = cache_dir / f"{filename}.parquet"
        if filepath.exists():
            df = pd.read_parquet(filepath)
            logger.info(f"Data loaded from cache: {filepath}")
            return df
        return None


from pathlib import Path
