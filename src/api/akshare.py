"""
AKShare 数据源适配器
提供对中国房地产数据的免费访问

AKShare 是开源项目，数据仅供学术研究参考，不构成投资建议
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# 尝试导入 akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare 未安装，请运行: pip install akshare")


# ---------------------------------------------------------------------------
# 房价数据
# ---------------------------------------------------------------------------

def fetch_house_price_index(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取中国房价指数
    
    Returns:
        包含日期和房价指数的 DataFrame
    """
    if not AKSHARE_AVAILABLE:
        return _fallback_house_price(start_date, end_date)
    
    try:
        # 尝试获取百城房价指数
        df = ak.macro_china_house_price()
        df["date"] = pd.to_datetime(df["日期"])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        return df
    except Exception as e:
        logger.warning(f"AKShare 房价数据获取失败: {e}，使用备用数据")
        return _fallback_house_price(start_date, end_date)


def _fallback_house_price(start_date: str, end_date: str) -> pd.DataFrame:
    """备用房价数据生成"""
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    # 模拟房价指数：2013-2021 上涨，之后下跌
    n = len(dates)
    base = 100
    trend = [base + 5 * i if i < 96 else base + 5 * 96 - 3 * (i - 96) for i in range(n)]
    trend = [t + (hash(str(i)) % 100 - 50) / 50 for i, t in enumerate(trend)]
    
    return pd.DataFrame({
        "date": dates,
        "house_price_index": trend,
    })


# ---------------------------------------------------------------------------
# 商品房销售与库存数据
# ---------------------------------------------------------------------------

def fetch_real_estate_data(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取商品房销售面积、待售面积等数据
    
    可用于计算 ACI (去化周期)
    """
    if not AKSHARE_AVAILABLE:
        return _fallback_real_estate(start_date, end_date)
    
    try:
        df = ak.macro_china_real_estate()
        df["date"] = pd.to_datetime(df["月份"])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        return df
    except Exception as e:
        logger.warning(f"AKShare 房地产数据获取失败: {e}")
        return _fallback_real_estate(start_date, end_date)


def _fallback_real_estate(start_date: str, end_date: str) -> pd.DataFrame:
    """备用房地产数据生成"""
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    n = len(dates)
    
    # 模拟商品房销售面积
    sales = [12000 + 100 * i - 0.5 * i ** 2 for i in range(n)]
    sales = [max(s, 5000) + (hash(str(i)) % 1000 - 500) for i, s in enumerate(sales)]
    
    # 模拟待售面积 (库存)
    inventory = [50000 + 50 * i for i in range(n)]
    
    return pd.DataFrame({
        "date": dates,
        "sales_area": sales,
        "inventory_area": inventory,
        "aci": [inv / max(sal, 1) for inv, sal in zip(inventory, sales)],
    })


# ---------------------------------------------------------------------------
# LPR 房贷利率数据
# ---------------------------------------------------------------------------

def fetch_lpr_data(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取贷款市场报价利率 (LPR)
    """
    if not AKSHARE_AVAILABLE:
        return _fallback_lpr(start_date, end_date)
    
    try:
        df = ak.macro_china_lpr()
        df["date"] = pd.to_datetime(df["日期"])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        return df
    except Exception as e:
        logger.warning(f"AKShare LPR 数据获取失败: {e}")
        return _fallback_lpr(start_date, end_date)


def _fallback_lpr(start_date: str, end_date: str) -> pd.DataFrame:
    """备用 LPR 数据生成"""
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    n = len(dates)
    
    # LPR 走势：2019 年推出后逐步下降
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

def fetch_land_data(city: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取土地成交数据
    
    Args:
        city: 城市名称（可选）
        start_date: 开始日期
        end_date: 结束日期
    """
    if not AKSHARE_AVAILABLE:
        return _fallback_land(start_date, end_date)
    
    try:
        if city:
            df = ak.land_city_data(city=city)
        else:
            df = ak.land_data()
        
        if "成交日期" in df.columns:
            df["date"] = pd.to_datetime(df["成交日期"])
        elif "日期" in df.columns:
            df["date"] = pd.to_datetime(df["日期"])
            
        return df
    except Exception as e:
        logger.warning(f"AKShare 土地数据获取失败: {e}")
        return _fallback_land(start_date, end_date)


def _fallback_land(start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
    """备用土地数据生成"""
    if start_date is None:
        start_date = "2013-01-01"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
        
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    n = len(dates)
    t = list(range(n))
    
    # 溢价率：从约 25% 线性下行
    premium = [max(0, 25 - 0.3 * ti + (hash(str(ti)) % 100 - 50) / 20) for ti in t]
    
    # 成交面积
    volume = [max(100, 1200 - 10 * ti + (hash(str(ti)) % 200 - 100)) for ti in t]
    
    return pd.DataFrame({
        "date": dates,
        "premium_rate": premium,
        "land_volume": volume,
    })


# ---------------------------------------------------------------------------
# 房地产投资数据
# ---------------------------------------------------------------------------

def fetch_real_estate_investment(start_date: str, end_date: str) -> pd.DataFrame:
    """获取房地产开发投资数据"""
    if not AKSHARE_AVAILABLE:
        return _fallback_investment(start_date, end_date)
    
    try:
        df = ak.macro_china_real_estate_investment()
        df["date"] = pd.to_datetime(df["时间"])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        return df
    except Exception as e:
        logger.warning(f"AKShare 投资数据获取失败: {e}")
        return _fallback_investment(start_date, end_date)


def _fallback_investment(start_date: str, end_date: str) -> pd.DataFrame:
    """备用投资数据"""
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    n = len(dates)
    investment = [10000 + 500 * i - 20 * i ** 2 for i in range(n)]
    
    return pd.DataFrame({
        "date": dates,
        "investment": investment,
    })


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def check_akshare_status() -> dict:
    """检查 AKShare 状态和可用数据"""
    status = {
        "available": AKSHARE_AVAILABLE,
        "version": None,
        "data_coverage": {},
    }
    
    if AKSHARE_AVAILABLE:
        try:
            status["version"] = ak.__version__
            
            # 测试各数据接口可用性
            test_funcs = [
                ("house_price", lambda: ak.macro_china_house_price()),
                ("real_estate", lambda: ak.macro_china_real_estate()),
                ("lpr", lambda: ak.macro_china_lpr()),
            ]
            
            for name, func in test_funcs:
                try:
                    func()
                    status["data_coverage"][name] = "可用"
                except:
                    status["data_coverage"][name] = "不可用"
                    
        except Exception as e:
            status["error"] = str(e)
    
    return status
