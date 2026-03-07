"""
宏观数据获取器 — Macro Data Fetcher
提供去化周期 (ACI) 历史数据。

数据源优先级:
    1. AKShare (免费，开源)
    2. East Money 东方财富 (免费)
    3. 模拟数据 (备用)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.db import get_engine
from src.utils.logger import get_logger
from src.utils.config import get as cfg_get
from src.repository.base import ACIRepository, CacheConfig

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 类型定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ACIData:
    """ACI 数据结构"""
    date: datetime
    sales_area: float
    inventory_area: float
    aci: float


# ---------------------------------------------------------------------------
# 数据获取函数
# ---------------------------------------------------------------------------

def fetch_aci_data(
    start_date: str = "2013-01-01",
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    获取去化周期 (ACI) 相关数据。
    ACI = 可售库存面积 / 月均销售面积

    数据源优先级:
        1. AKShare (免费)
        2. East Money (免费)
        3. 模拟数据 (备用)

    Args:
        start_date: 起始日期字符串 (YYYY-MM-DD)
        end_date: 结束日期字符串，默认为今日

    Returns:
        包含 ['date', 'sales_area', 'inventory_area', 'aci'] 列的 DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"获取 ACI 数据: {start_date} → {end_date}")

    # 尝试 NBS Client
    try:
        from src.api.nbs_client import NBSClient
        client = NBSClient()
        df = client.fetch_real_estate_data(start_date, end_date)
        if df is not None and not df.empty:
            logger.info("✅ ACI 数据获取成功 (NBS Client)")
            return _normalize_aci_df(df)
    except Exception as e:
        logger.warning(f"NBS Client 获取失败: {e}")

    # 尝试 East Money
    try:
        from src.api import eastmoney
        df = eastmoney.fetch_real_estate_sales()
        if df is not None and not df.empty:
            # 添加库存数据
            df["inventory_area"] = df.get("inventory_area", df["sales_area"] * 20)
            df["aci"] = df["inventory_area"] / df["sales_area"]
            logger.info("✅ ACI 数据获取成功 (East Money)")
            return _normalize_aci_df(df)
    except Exception as e:
        logger.warning(f"East Money 获取失败: {e}")

    # 降级到模拟数据
    logger.info("📊 使用 ACI 模拟数据")
    return _generate_mock_aci(start_date, end_date)


def _normalize_aci_df(df: pd.DataFrame) -> pd.DataFrame:
    """标准化 ACI DataFrame 格式"""
    df = df.copy()
    
    # 确保有 date 列
    if "date" not in df.columns:
        if "月份" in df.columns:
            df["date"] = pd.to_datetime(df["月份"])
        elif "日期" in df.columns:
            df["date"] = pd.to_datetime(df["日期"])
    
    # 确保有必要的列
    if "sales_area" not in df.columns:
        if "商品房销售面积" in df.columns:
            df["sales_area"] = df["商品房销售面积"]
        else:
            df["sales_area"] = 10000  # 默认值
    
    if "inventory_area" not in df.columns:
        if "商品房待售面积" in df.columns:
            df["inventory_area"] = df["商品房待售面积"]
        else:
            df["inventory_area"] = df["sales_area"] * 20
    
    # 计算 ACI
    if "aci" not in df.columns:
        df["aci"] = df["inventory_area"] / df["sales_area"]
    
    # 只保留需要的列
    result = pd.DataFrame({
        "date": pd.to_datetime(df["date"]),
        "sales_area": df["sales_area"],
        "inventory_area": df["inventory_area"],
        "aci": df["aci"],
    })
    
    return result.dropna()


def _generate_mock_aci(
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    生成 ACI 模拟数据
    
    模拟逻辑:
        - 销售面积: 长期趋势 + 季节性 + 噪声
        - 库存面积: 累计计算 (入库 - 销售)
        - ACI: 库存 / 月均销售
    """
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    n = len(dates)
    t = np.arange(n)

    # 模拟月度销售面积
    trend_sales = 12000 + 100 * t - 0.8 * t ** 2
    seasonality = 1500 * np.sin(2 * np.pi * t / 12)
    sales_area = trend_sales + seasonality + np.random.default_rng().normal(0, 800, n)
    sales_area = np.maximum(sales_area, 2000)

    # 模拟库存面积
    inventory_area = np.zeros(n)
    inventory_area[0] = 60000
    for i in range(1, n):
        completions = 11000 + 30 * t[i] + np.random.default_rng().normal(0, 500)
        inventory_area[i] = inventory_area[i - 1] + completions - sales_area[i]
        inventory_area[i] = max(inventory_area[i], 10000)

    df = pd.DataFrame({
        "date": dates,
        "sales_area": sales_area,
        "inventory_area": inventory_area,
    })
    df["aci"] = df["inventory_area"] / df["sales_area"]

    logger.info(
        f"ACI 模拟数据生成完毕，共 {len(df)} 条记录。"
        f" ACI 区间: [{df['aci'].min():.1f}, {df['aci'].max():.1f}] 月"
    )
    return df


def save_aci_to_db(
    start_date: Optional[str] = None,
    force_update: bool = False,
) -> int:
    """
    获取 ACI 数据并写入数据库。
    
    Args:
        start_date: 开始日期，默认从配置读取
        force_update: 是否强制更新（忽略缓存）
        
    Returns:
        保存的记录数
    """
    if start_date is None:
        start_date = cfg_get("data.start_date", "2013-01-01")
    
    # 使用仓储层（带缓存）
    engine = get_engine()
    cache_config = CacheConfig(enabled=not force_update)
    repo = ACIRepository(engine, cache_config)
    
    # 检查是否需要更新
    if not force_update:
        existing = repo.get()
        if not existing.empty:
            logger.info(f"使用现有 ACI 数据: {len(existing)} 条")
            return len(existing)
    
    # 获取新数据
    df = fetch_aci_data(start_date=start_date)
    repo.save(df)
    
    return len(df)


# ---------------------------------------------------------------------------
# 主程序入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    save_aci_to_db()
