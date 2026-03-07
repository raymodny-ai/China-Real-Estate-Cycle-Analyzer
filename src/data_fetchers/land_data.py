"""
土地数据获取器 — Land Data Fetcher
提供土地溢价拍买率 (LPR - Land Premium Rate) 数据。

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
from src.repository.base import LPRRepository, CacheConfig

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 类型定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LPRData:
    """LPR 数据结构"""
    date: datetime
    premium_rate: float  # 土地溢价率 (%)
    land_volume: float   # 土地成交面积 (万㎡)


# ---------------------------------------------------------------------------
# 数据获取函数
# ---------------------------------------------------------------------------

def fetch_lpr_data(
    start_date: str = "2013-01-01",
    end_date: Optional[str] = None,
    city: Optional[str] = None,
) -> pd.DataFrame:
    """
    获取土地溢价拍买率 (LPR) 数据。

    数据特征:
        - 2013-2019: 溢价率较高（15-30%），土地市场热度较高
        - 2020-今:   溢价率持续收窄，趋近于零（流拍率上升）

    数据源优先级:
        1. AKShare (免费)
        2. East Money (免费)
        3. 模拟数据 (备用)

    Args:
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期，默认今日
        city: 城市名称（可选）

    Returns:
        包含 ['date', 'premium_rate', 'land_volume'] 的月度 DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"获取 LPR 数据: {start_date} → {end_date}")

    # 尝试 Land Client
    try:
        from src.api.land_client import LandClient
        client = LandClient()
        df = client.fetch_premium_data(start_date=start_date, end_date=end_date, city=city)
        if df is not None and not df.empty:
            logger.info("✅ LPR 数据获取成功 (Land Client)")
            return _normalize_lpr_df(df)
    except Exception as e:
        logger.warning(f"Land Client 获取失败: {e}")

    # 尝试 East Money
    try:
        from src.api import eastmoney
        df = eastmoney.fetch_land_transaction(city=city)
        if df is not None and not df.empty:
            logger.info("✅ LPR 数据获取成功 (East Money)")
            return _normalize_lpr_df(df)
    except Exception as e:
        logger.warning(f"East Money 获取失败: {e}")

    # 降级到模拟数据
    logger.info("📊 使用 LPR 模拟数据")
    return _generate_mock_lpr(start_date, end_date)


def _normalize_lpr_df(df: pd.DataFrame) -> pd.DataFrame:
    """标准化 LPR DataFrame 格式"""
    df = df.copy()
    
    # 确保有 date 列
    if "date" not in df.columns:
        for col in ["成交日期", "日期", "月份"]:
            if col in df.columns:
                df["date"] = pd.to_datetime(df[col])
                break
    
    # 确保有 premium_rate 列
    if "premium_rate" not in df.columns:
        for col in ["溢价率", "土地溢价率", "溢价率(%)"]:
            if col in df.columns:
                df["premium_rate"] = df[col]
                break
    
    # 确保有 land_volume 列
    if "land_volume" not in df.columns:
        for col in ["成交面积", "土地成交面积", "成交量"]:
            if col in df.columns:
                df["land_volume"] = df[col]
                break
    
    # 填充默认值
    if "premium_rate" not in df.columns:
        df["premium_rate"] = 15.0
    if "land_volume" not in df.columns:
        df["land_volume"] = 1000.0
    
    result = pd.DataFrame({
        "date": pd.to_datetime(df["date"]),
        "premium_rate": df["premium_rate"].fillna(0),
        "land_volume": df["land_volume"].fillna(1000),
    })
    
    # 溢价率不能为负
    result["premium_rate"] = result["premium_rate"].clip(lower=0)
    
    return result.dropna().sort_values("date")


def _generate_mock_lpr(
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    生成 LPR 模拟数据
    
    数据特征:
        - 溢价率：从约 25% 线性下行，叠加季节性和随机噪声
        - 成交土地面积：同步下降
    """
    dates = pd.date_range(start=start_date, end=end_date, freq="ME")
    n = len(dates)
    t = np.arange(n)

    # 溢价率
    premium_rate = (
        25 
        - 0.25 * t 
        + 3 * np.sin(2 * np.pi * t / 12) 
        + np.random.default_rng().normal(0, 2, n)
    )
    premium_rate = np.maximum(premium_rate, 0.0)

    # 成交面积
    land_volume = 1200 - 8 * t + np.random.default_rng().normal(0, 50, n)
    land_volume = np.maximum(land_volume, 100.0)

    df = pd.DataFrame({
        "date": dates,
        "premium_rate": premium_rate,
        "land_volume": land_volume,
    })

    logger.info(
        f"LPR 模拟数据生成完毕，共 {len(df)} 条记录。"
        f" 溢价率区间: [{df['premium_rate'].min():.1f}%, {df['premium_rate'].max():.1f}%]"
    )
    return df


def save_lpr_to_db(
    start_date: Optional[str] = None,
    force_update: bool = False,
) -> int:
    """
    获取 LPR 数据并写入数据库。
    
    Args:
        start_date: 开始日期，默认从配置读取
        force_update: 是否强制更新
        
    Returns:
        保存的记录数
    """
    if start_date is None:
        start_date = cfg_get("data.start_date", "2013-01-01")
    
    engine = get_engine()
    cache_config = CacheConfig(enabled=not force_update)
    repo = LPRRepository(engine, cache_config)
    
    # 检查是否需要更新
    if not force_update:
        existing = repo.get()
        if not existing.empty:
            logger.info(f"使用现有 LPR 数据: {len(existing)} 条")
            return len(existing)
    
    # 获取新数据
    df = fetch_lpr_data(start_date=start_date)
    repo.save(df)
    
    return len(df)


# ---------------------------------------------------------------------------
# 主程序入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    save_lpr_to_db()
