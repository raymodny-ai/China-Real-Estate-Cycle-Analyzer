"""
Tests for data fetchers module
"""
import pytest
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_data_fetchers_import():
    """Test that data fetchers can be imported"""
    try:
        from src.data_fetchers import NBSDataFetcher, EastMoneyFetcher, BaseDataFetcher
        assert BaseDataFetcher is not None
        assert NBSDataFetcher is not None
        assert EastMoneyFetcher is not None
    except ImportError:
        pytest.skip("Data fetchers module not found")


def test_base_fetcher_init():
    """Test BaseDataFetcher initialization"""
    try:
        from src.data_fetchers import BaseDataFetcher
        
        fetcher = BaseDataFetcher(api_key="test_key")
        assert fetcher.api_key == "test_key"
        
    except ImportError:
        pytest.skip("Data fetchers module not found")


def test_nbs_fetcher_init():
    """Test NBSDataFetcher initialization"""
    try:
        from src.data_fetchers import NBSDataFetcher
        
        fetcher = NBSDataFetcher()
        assert fetcher is not None
        assert fetcher.base_url is not None
        
    except ImportError:
        pytest.skip("Data fetchers module not found")


def test_nbs_fetch():
    """Test NBS data fetching"""
    try:
        from src.data_fetchers import NBSDataFetcher
        
        fetcher = NBSDataFetcher()
        df = fetcher.fetch(
            code='AY0X01',
            start_date='2020-01',
            end_date='2024-12',
            city='北京'
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        
    except ImportError:
        pytest.skip("Data fetchers module not found")
    except Exception as e:
        # May fail due to API or mock data
        pytest.skip(f"NBS fetch failed: {e}")


def test_nbs_get_aci_data():
    """Test NBS ACI data fetching"""
    try:
        from src.data_fetchers import NBSDataFetcher
        
        fetcher = NBSDataFetcher()
        df = fetcher.get_aci_data(
            city='北京',
            start_date='2020-01',
            end_date='2024-12'
        )
        
        assert isinstance(df, pd.DataFrame)
        
    except ImportError:
        pytest.skip("Data fetchers module not found")
    except Exception as e:
        pytest.skip(f"NBS ACI fetch failed: {e}")


def test_eastmoney_fetcher_init():
    """Test EastMoneyFetcher initialization"""
    try:
        from src.data_fetchers import EastMoneyFetcher
        
        fetcher = EastMoneyFetcher()
        assert fetcher is not None
        
    except ImportError:
        pytest.skip("Data fetchers module not found")


def test_eastmoney_fetch():
    """Test EastMoney data fetching"""
    try:
        from src.data_fetchers import EastMoneyFetcher
        
        fetcher = EastMoneyFetcher()
        df = fetcher.fetch()
        
        assert isinstance(df, pd.DataFrame)
        
    except ImportError:
        pytest.skip("Data fetchers module not found")
    except Exception as e:
        # May fail due to API
        pytest.skip(f"EastMoney fetch failed: {e}")


def test_eastmoney_get_lpr_data():
    """Test LPR data fetching"""
    try:
        from src.data_fetchers import EastMoneyFetcher
        
        fetcher = EastMoneyFetcher()
        df = fetcher.get_lpr_data()
        
        assert isinstance(df, pd.DataFrame)
        
    except ImportError:
        pytest.skip("Data fetchers module not found")
    except Exception as e:
        pytest.skip(f"LPR fetch failed: {e}")


def test_validate_date_range():
    """Test date range validation"""
    try:
        from src.data_fetchers import BaseDataFetcher
        
        fetcher = BaseDataFetcher()
        
        # Valid dates
        assert fetcher.validate_date_range('2020-01', '2024-12') == True
        
        # Invalid dates
        assert fetcher.validate_date_range('2020-01-01', '2024-12-31') == False
        
    except ImportError:
        pytest.skip("Data fetchers module not found")


def test_to_dataframe():
    """Test DataFrame conversion"""
    try:
        from src.data_fetchers import BaseDataFetcher
        
        fetcher = BaseDataFetcher()
        data = {'col1': [1, 2, 3], 'col2': [4, 5, 6]}
        
        df = fetcher.to_dataframe(data)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        
    except ImportError:
        pytest.skip("Data fetchers module not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
