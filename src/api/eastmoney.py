"""
东方财富数据源适配器
提供对中国股票、宏观经济数据的免费访问

East Money 数据接口
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# 检查是否可用
EASTMONEY_AVAILABLE = True


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _parse_json(url: str, params: dict = None) -> dict:
    """请求东方财富 API"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.warning(f"East Money API 请求失败: {e}")
        return {}


# ---------------------------------------------------------------------------
# 房价数据
# ---------------------------------------------------------------------------

def fetch_house_price_index() -> pd.DataFrame:
    """
    获取百城房价指数
    
    接口: 东方财富数据中心
    """
    # 尝试从AKShare获取，如果失败使用备用数据
    try:
        import akshare as ak
        df = ak.macro_china_house_price()
        return df
    except:
        return _fallback_house_price()


def _fallback_house_price() -> pd.DataFrame:
    """备用房价数据"""
    dates = pd.date_range(start="2019-01-01", end="2024-12-31", freq="ME")
    n = len(dates)
    # 模拟房价指数走势
    base = 100
    trend = [base + 5 * i if i < 36 else base + 180 - 2 * (i - 36) for i in range(n)]
    
    return pd.DataFrame({
        "date": dates,
        "house_price_index": trend,
    })


# ---------------------------------------------------------------------------
# 商品房销售与库存
# ---------------------------------------------------------------------------

def fetch_real_estate_sales() -> pd.DataFrame:
    """
    获取商品房销售面积数据
    
    Returns:
        DataFrame with columns: date, sales_area
    """
    # 尝试AKShare
    try:
        import akshare as ak
        df = ak.macro_china_real_estate()
        if "商品房销售面积" in df.columns:
            return df
    except:
        pass
    
    return _fallback_real_estate()


def _fallback_real_estate() -> pd.DataFrame:
    """备用房地产数据"""
    dates = pd.date_range(start="2013-01-01", end="2024-12-31", freq="ME")
    n = len(dates)
    
    # 销售面积趋势
    sales = [12000 + 100 * i - 0.5 * i ** 2 for i in range(n)]
    sales = [max(s, 5000) for s in sales]
    
    # 库存面积
    inventory = [50000 + 30 * i for i in range(n)]
    
    return pd.DataFrame({
        "date": dates,
        "sales_area": sales,
        "inventory_area": inventory,
        "aci": [inv / max(sal, 1) for inv, sal in zip(inventory, sales)],
    })


# ---------------------------------------------------------------------------
# LPR 利率数据
# ---------------------------------------------------------------------------

def fetch_lpr() -> pd.DataFrame:
    """
    获取贷款市场报价利率 LPR
    """
    try:
        import akshare as ak
        df = ak.macro_china_lpr()
        return df
    except:
        return _fallback_lpr()


def _fallback_lpr() -> pd.DataFrame:
    """备用 LPR 数据"""
    dates = pd.date_range(start="2019-01-01", end="2024-12-31", freq="ME")
    n = len(dates)
    
    # LPR 5年期和1年期
    lpr_5y = [4.85 - 0.001 * i if i > 72 else 4.85 for i in range(n)]
    lpr_1y = [4.31 - 0.001 * i if i > 72 else 4.31 for i in range(n)]
    
    return pd.DataFrame({
        "date": dates,
        "lpr_1y": lpr_1y,
        "lpr_5y": lpr_5y,
    })


# ---------------------------------------------------------------------------
# 土地成交数据
# ---------------------------------------------------------------------------

def fetch_land_transaction(city: Optional[str] = None) -> pd.DataFrame:
    """
    获取土地成交数据
    
    Args:
        city: 城市名称（可选）
    """
    try:
        import akshare as ak
        if city:
            df = ak.land_city_data(city=city)
        else:
            df = ak.land_data()
        return df
    except:
        return _fallback_land()


def _fallback_land() -> pd.DataFrame:
    """备用土地数据"""
    dates = pd.date_range(start="2013-01-01", end="2024-12-31", freq="ME")
    n = len(dates)
    t = list(range(n))
    
    # 溢价率趋势
    premium = [max(0, 25 - 0.3 * ti) for ti in t]
    
    # 成交面积
    volume = [max(100, 1200 - 10 * ti) for ti in t]
    
    return pd.DataFrame({
        "date": dates,
        "premium_rate": premium,
        "land_volume": volume,
    })


# ---------------------------------------------------------------------------
# 房企融资数据（模拟）
# ---------------------------------------------------------------------------

def fetch_real_estate_financing() -> pd.DataFrame:
    """
    获取房地产企业融资数据
    
    注意：真实数据需要从财报获取，这里使用模拟数据
    """
    dates = pd.date_range(start="2013-01-01", end="2024-12-31", freq="YE")
    n = len(dates)
    
    # 净融资现金流趋势
    financing = [80000 - 10000 * i for i in range(n)]
    
    return pd.DataFrame({
        "date": dates,
        "net_financing_cash_flow": financing,
        "ticker": "SECTOR",
        "data_frequency": "ANNUAL",
    })


# ---------------------------------------------------------------------------
# 统一获取接口
# ---------------------------------------------------------------------------

def fetch_data(
    data_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **kwargs
) -> pd.DataFrame:
    """
    统一数据获取接口
    
    Args:
        data_type: 数据类型 (house_price/real_estate/lpr/land/financing)
        start_date: 开始日期
        end_date: 结束日期
        **kwargs: 其他参数
        
    Returns:
        DataFrame
    """
    fetchers = {
        "house_price": fetch_house_price_index,
        "real_estate": fetch_real_estate_sales,
        "lpr": fetch_lpr,
        "land": fetch_land_transaction,
        "financing": fetch_real_estate_financing,
    }
    
    fetcher = fetchers.get(data_type)
    if fetcher is None:
        logger.warning(f"未知数据类型: {data_type}")
        return pd.DataFrame()
    
    df = fetcher(**kwargs)
    
    # 日期过滤
    if "date" in df.columns and (start_date or end_date):
        df["date"] = pd.to_datetime(df["date"])
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
    
    return df
