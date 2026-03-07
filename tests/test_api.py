"""
API 模块单元测试
tests/test_api.py
"""
from __future__ import annotations

import pytest
import pandas as pd
from datetime import datetime

from src.api.base import (
    DataSourceConfig,
    DataSourceFactory,
    fetch_with_fallback,
)


class TestDataSourceConfig:
    """数据源配置测试"""

    def test_default_config(self):
        config = DataSourceConfig(name="test")
        assert config.name == "test"
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_config_with_params(self):
        config = DataSourceConfig(
            name="custom",
            api_key="test_key",
            base_url="https://api.test.com",
            timeout=60,
        )
        assert config.name == "custom"
        assert config.api_key == "test_key"
        assert config.base_url == "https://api.test.com"
        assert config.timeout == 60


class TestDataSourceFactory:
    """数据源工厂测试"""

    def test_create_nbs_source(self):
        source = DataSourceFactory.create("nbs")
        assert source is not None
        assert isinstance(source.name, str)

    def test_create_choice_source(self):
        source = DataSourceFactory.create("choice")
        assert source is not None

    def test_create_cric_source(self):
        source = DataSourceFactory.create("cric")
        assert source is not None

    def test_invalid_source_type(self):
        with pytest.raises(ValueError, match="未知数据源类型"):
            DataSourceFactory.create("invalid_source")


class TestFetchWithFallback:
    """降级策略测试"""

    def test_fetch_with_fallback_returns_result(self):
        """测试 fetch_with_fallback 返回正确结构"""
        result = fetch_with_fallback(
            source_type="nbs",
            fetch_func="fetch",
            indicator="sales_area",
            start_date="2023-01-01",
            end_date="2023-12-31",
        )
        
        assert hasattr(result, "success")
        assert hasattr(result, "data")
        assert hasattr(result, "source")
        assert isinstance(result.data, pd.DataFrame)

    def test_fallback_to_mock(self):
        """测试 API 失败时降级到模拟数据"""
        result = fetch_with_fallback(
            source_type="choice",
            fetch_func="fetch_fpi",
            tickers=["000002.SZ"],
            start_year=2020,
            end_year=2024,
        )
        
        # 应该成功获取模拟数据
        assert result.success is True
        assert not result.data.empty
        assert "net_financing_cash_flow" in result.data.columns


class TestNBSDataSource:
    """国家统计局数据源测试"""

    def test_mock_data_generation(self):
        """测试模拟数据生成"""
        from src.api.base import NBSDataSource, DataSourceConfig
        
        config = DataSourceConfig(name="nbs")
        source = NBSDataSource(config)
        
        df = source._generate_mock_data(
            indicator="sales_area",
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        assert not df.empty
        assert "date" in df.columns
        assert "sales_area" in df.columns

    def test_indicator_codes(self):
        """测试指标代码映射"""
        from src.api.base import NBSDataSource
        
        codes = NBSDataSource.INDICATOR_CODES
        assert "sales_area" in codes
        assert "inventory_area" in codes
        assert codes["sales_area"] == "E0101"


class TestChoiceDataSource:
    """东方财富数据源测试"""

    def test_mock_fpi_generation(self):
        """测试模拟 FPI 数据生成"""
        from src.api.base import ChoiceDataSource, DataSourceConfig
        
        config = DataSourceConfig(name="choice")
        source = ChoiceDataSource(config)
        
        df = source._generate_mock_fpi(2020, 2024)
        
        assert not df.empty
        assert "date" in df.columns
        assert "net_financing_cash_flow" in df.columns
        assert "data_frequency" in df.columns
        assert df["data_frequency"].iloc[0] == "ANNUAL"

    def test_fpi_trend_decreasing(self):
        """测试 FPI 趋势为负（资金链收紧）"""
        from src.api.base import ChoiceDataSource, DataSourceConfig
        
        config = DataSourceConfig(name="choice")
        source = ChoiceDataSource(config)
        
        df = source._generate_mock_fpi(2015, 2024)
        
        # 后期年份净融资应该低于早期
        first_val = df["net_financing_cash_flow"].iloc[0]
        last_val = df["net_financing_cash_flow"].iloc[-1]
        assert last_val < first_val


class TestCRICDataSource:
    """CRIC 数据源测试"""

    def test_mock_land_generation(self):
        """测试模拟土地数据生成"""
        from src.api.base import CRICDataSource, DataSourceConfig
        
        config = DataSourceConfig(name="cric")
        source = CRICDataSource(config)
        
        df = source._generate_mock_land("2020-01-01", "2023-12-31")
        
        assert not df.empty
        assert "date" in df.columns
        assert "premium_rate" in df.columns
        assert "land_volume" in df.columns
        assert (df["premium_rate"] >= 0).all()

    def test_premium_rate_decreasing(self):
        """测试溢价率趋势下降"""
        from src.api.base import CRICDataSource, DataSourceConfig
        
        config = DataSourceConfig(name="cric")
        source = CRICDataSource(config)
        
        df = source._generate_mock_land("2015-01-01", "2024-12-31")
        
        # 按时间排序后，早期溢价率应高于后期
        df = df.sort_values("date")
        early_avg = df["premium_rate"].head(12).mean()
        late_avg = df["premium_rate"].tail(12).mean()
        assert late_avg < early_avg
