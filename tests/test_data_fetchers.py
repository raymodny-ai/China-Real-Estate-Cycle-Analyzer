"""
数据获取器单元测试
tests/test_data_fetchers.py
"""
from __future__ import annotations

import pytest
import pandas as pd
from datetime import datetime
import numpy as np


class TestMacroDataFetcher:
    """宏观数据获取器测试"""

    def test_fetch_aci_data_returns_dataframe(self):
        """测试 fetch_aci_data 返回正确的 DataFrame 结构"""
        from src.data_fetchers.macro_data import fetch_aci_data
        
        df = fetch_aci_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "sales_area" in df.columns
        assert "inventory_area" in df.columns
        assert "aci" in df.columns

    def test_aci_calculation(self):
        """测试 ACI 计算逻辑"""
        from src.data_fetchers.macro_data import fetch_aci_data
        
        df = fetch_aci_data(
            start_date="2020-01-01",
            end_date="2020-12-31",
        )
        
        # ACI = 库存 / 销售
        expected_aci = df["inventory_area"] / df["sales_area"]
        assert np.allclose(df["aci"], expected_aci)

    def test_aci_values_reasonable(self):
        """测试 ACI 值在合理范围内"""
        from src.data_fetchers.macro_data import fetch_aci_data
        
        df = fetch_aci_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        # ACI 应该为正数
        assert (df["aci"] > 0).all()
        # ACI 通常不会超过 100 个月
        assert (df["aci"] < 100).all()

    def test_date_range(self):
        """测试日期范围正确"""
        from src.data_fetchers.macro_data import fetch_aci_data
        
        start = "2020-01-01"
        end = "2020-12-31"
        
        df = fetch_aci_data(start_date=start, end_date=end)
        
        assert df["date"].min().year == 2020
        assert df["date"].max().year == 2020


class TestFinancialDataFetcher:
    """金融数据获取器测试"""

    def test_fetch_fpi_data_returns_dataframe(self):
        """测试 fetch_fpi_data 返回正确的 DataFrame"""
        from src.data_fetchers.financial_data import fetch_fpi_data
        
        df = fetch_fpi_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "net_financing_cash_flow" in df.columns
        assert "data_frequency" in df.columns

    def test_fpi_is_annual_frequency(self):
        """测试 FPI 数据频率为年度"""
        from src.data_fetchers.financial_data import fetch_fpi_data
        
        df = fetch_fpi_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        # 年度数据每年应该只有一条
        df["year"] = pd.to_datetime(df["date"]).dt.year
        year_counts = df.groupby("year").size()
        assert (year_counts <= 1).all()

    def test_fpi_decreasing_trend(self):
        """测试 FPI 长期下降趋势"""
        from src.data_fetchers.financial_data import fetch_fpi_data
        
        df = fetch_fpi_data(
            start_date="2015-01-01",
            end_date="2024-12-31",
        )
        
        df = df.sort_values("date")
        
        # 使用线性回归检查趋势
        y = df["net_financing_cash_flow"].values
        x = np.arange(len(y))
        slope = np.polyfit(x, y, 1)[0]
        
        assert slope < 0  # 应该是负斜率


class TestLandDataFetcher:
    """土地数据获取器测试"""

    def test_fetch_lpr_data_returns_dataframe(self):
        """测试 fetch_lpr_data 返回正确的 DataFrame"""
        from src.data_fetchers.land_data import fetch_lpr_data
        
        df = fetch_lpr_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "premium_rate" in df.columns
        assert "land_volume" in df.columns

    def test_premium_rate_non_negative(self):
        """测试溢价率非负"""
        from src.data_fetchers.land_data import fetch_lpr_data
        
        df = fetch_lpr_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        assert (df["premium_rate"] >= 0).all()

    def test_land_volume_positive(self):
        """测试土地成交面积为正"""
        from src.data_fetchers.land_data import fetch_lpr_data
        
        df = fetch_lpr_data(
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
        
        assert (df["land_volume"] > 0).all()

    def test_premium_rate_decreasing(self):
        """测试溢价率长期下降"""
        from src.data_fetchers.land_data import fetch_lpr_data
        
        df = fetch_lpr_data(
            start_date="2015-01-01",
            end_date="2024-12-31",
        )
        
        df = df.sort_values("date")
        
        # 比较前后两个时期的平均值
        n = len(df)
        early_avg = df["premium_rate"].iloc[:n//2].mean()
        late_avg = df["premium_rate"].iloc[n//2:].mean()
        
        assert late_avg < early_avg


class TestDataIntegration:
    """数据集成测试"""

    def test_all_fetchers_work_together(self):
        """测试所有数据获取器可以协同工作"""
        from src.data_fetchers import (
            macro_data,
            financial_data,
            land_data,
        )
        
        start = "2022-01-01"
        end = "2023-12-31"
        
        aci_df = macro_data.fetch_aci_data(start, end)
        fpi_df = financial_data.fetch_fpi_data(start, end)
        lpr_df = land_data.fetch_lpr_data(start, end)
        
        assert not aci_df.empty
        assert not fpi_df.empty
        assert not lpr_df.empty

    def test_data_date_alignment(self):
        """测试不同数据源日期对齐"""
        from src.data_fetchers import (
            macro_data,
            land_data,
        )
        
        start = "2020-01-01"
        end = "2023-12-31"
        
        aci_df = macro_data.fetch_aci_data(start, end)
        lpr_df = land_data.fetch_lpr_data(start, end)
        
        # 检查日期范围一致
        assert aci_df["date"].min() == lpr_df["date"].min()
        assert aci_df["date"].max() == lpr_df["date"].max()
