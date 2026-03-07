"""
AKShare 数据源单元测试
tests/test_akshare.py
"""
from __future__ import annotations

import pytest
import pandas as pd
from datetime import datetime


class TestAKShareAvailability:
    """AKShare 可用性测试"""

    def test_akshare_importable(self):
        """测试 AKShare 是否可导入"""
        try:
            import akshare as ak
            assert ak.__version__ is not None
        except ImportError:
            pytest.skip("AKShare 未安装")

    def test_akshare_status_check(self):
        """测试 AKShare 状态检查函数"""
        from src.api.akshare import check_akshare_status
        
        status = check_akshare_status()
        
        # 应该返回可用状态
        assert "available" in status
        assert "version" in status
        assert "data_coverage" in status


class TestHousePriceData:
    """房价数据测试"""

    def test_fetch_house_price_index(self):
        """测试房价指数获取"""
        from src.api.akshare import fetch_house_price_index
        
        df = fetch_house_price_index("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns

    def test_fallback_house_price(self):
        """测试备用房价数据"""
        from src.api.akshare import _fallback_house_price
        
        df = _fallback_house_price("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "house_price_index" in df.columns


class TestRealEstateData:
    """房地产数据测试"""

    def test_fetch_real_estate_data(self):
        """测试房地产数据获取"""
        from src.api.akshare import fetch_real_estate_data
        
        df = fetch_real_estate_data("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns

    def test_fallback_real_estate(self):
        """测试备用房地产数据"""
        from src.api.akshare import _fallback_real_estate
        
        df = _fallback_real_estate("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "sales_area" in df.columns
        assert "inventory_area" in df.columns
        assert "aci" in df.columns


class TestLPRData:
    """LPR 数据测试"""

    def test_fetch_lpr_data(self):
        """测试 LPR 数据获取"""
        from src.api.akshare import fetch_lpr_data
        
        df = fetch_lpr_data("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns

    def test_fallback_lpr(self):
        """测试备用 LPR 数据"""
        from src.api.akshare import _fallback_lpr
        
        df = _fallback_lpr("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "lpr_1y" in df.columns
        assert "lpr_5y" in df.columns


class TestLandData:
    """土地数据测试"""

    def test_fetch_land_data(self):
        """测试土地数据获取"""
        from src.api.akshare import fetch_land_data
        
        df = fetch_land_data(start_date="2020-01-01", end_date="2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_fallback_land(self):
        """测试备用土地数据"""
        from src.api.akshare import _fallback_land
        
        df = _fallback_land("2020-01-01", "2023-12-31")
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "premium_rate" in df.columns
        assert "land_volume" in df.columns


class TestDataIntegration:
    """数据集成测试"""

    def test_all_data_fetchers(self):
        """测试所有 AKShare 数据获取函数"""
        from src.api.akshare import (
            fetch_house_price_index,
            fetch_real_estate_data,
            fetch_lpr_data,
            fetch_land_data,
        )
        
        start = "2022-01-01"
        end = "2022-12-31"
        
        # 所有函数应该返回 DataFrame
        assert isinstance(fetch_house_price_index(start, end), pd.DataFrame)
        assert isinstance(fetch_real_estate_data(start, end), pd.DataFrame)
        assert isinstance(fetch_lpr_data(start, end), pd.DataFrame)
        assert isinstance(fetch_land_data(start_date=start, end_date=end), pd.DataFrame)

    def test_date_range_filtering(self):
        """测试日期范围过滤"""
        from src.api.akshare import fetch_house_price_index
        
        df = fetch_house_price_index("2022-01-01", "2022-12-31")
        
        df["date"] = pd.to_datetime(df["date"])
        
        assert df["date"].min().year >= 2022
        assert df["date"].max().year <= 2022
