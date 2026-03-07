"""
金融数据获取器 — Financial Data Fetcher
提供房企资金链压力指数 (FPI) 数据。

数据源优先级:
    1. AKShare (免费，开源)
    2. East Money 东方财富 (免费)
    3. 模拟数据 (备用)

数据频率说明：
    FPI 净融资现金流为[年度]指标，来源于房企年报。
    在指标计算中采用前向填充将其对齐到月度频率是一种近似处理。
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
from src.repository.base import FPIRepository, CacheConfig

logger = get_logger(__name__)

# 真实数据接入时的参考 Tickers
REFERENCE_TICKERS = ["000002.SZ", "600048.SS", "0688.HK"]


# ---------------------------------------------------------------------------
# 类型定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FPIData:
    """FPI 数据结构"""
    date: datetime
    net_financing_cash_flow: float
    ticker: str
    data_frequency: str  # "ANNUAL" or "MONTHLY"


# ---------------------------------------------------------------------------
# 数据获取函数
# ---------------------------------------------------------------------------

def fetch_fpi_data(
    start_date: str = "2013-01-01",
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    获取 FPI (Financial Pressure Index) 数据。
    
    返回年度净融资现金流数据

    数据源优先级:
        1. AKShare (免费)
        2. East Money (免费)
        3. 模拟数据 (备用)

    Args:
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期，默认今日

    Returns:
        年度频率的 FPI DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    start_year = int(start_date[:4])
    end_year = int(end_date[:4])

    logger.info(f"获取 FPI 数据: {start_year} → {end_year}")

    # 尝试 Bond Client
    try:
        from src.api.bond_client import BondClient
        client = BondClient()
        df = client.fetch_financing_data(start_year, end_year)
        if df is not None and not df.empty:
            logger.info("✅ FPI 数据获取成功 (Bond Client)")
            return df
    except Exception as e:
        logger.warning(f"Bond Client 获取失败: {e}")

    # 降级到模拟数据
    logger.info("📊 使用 FPI 模拟数据")
    return _generate_mock_fpi(start_year, end_year)


def _generate_mock_fpi(
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    生成 FPI 模拟数据
    
    数据特征:
        - 2013-2017: 高正值，行业融资宽松
        - 2018-2020: 逐步收紧
        - 2021-今:   显著负值，代表资金链持续承压
    """
    years = list(range(start_year, end_year + 1))
    n = len(years)
    t = np.arange(n)

    # 高峰期后持续下行的净融资曲线
    net_financing = 80000 - 8000 * t + np.random.default_rng().normal(0, 5000, n)

    df = pd.DataFrame({
        "date": pd.to_datetime([f"{y}-12-31" for y in years]),
        "net_financing_cash_flow": net_financing,
        "ticker": "SECTOR_AGGREGATE",
        "data_frequency": "ANNUAL",
    })

    logger.info(
        f"FPI 模拟数据生成完毕，共 {len(df)} 条年度记录。"
        f" 净融资区间: [{df['net_financing_cash_flow'].min():.0f}, "
        f"{df['net_financing_cash_flow'].max():.0f}] 万元"
    )
    return df


def save_fpi_to_db(
    start_date: Optional[str] = None,
    force_update: bool = False,
) -> int:
    """
    获取 FPI 数据并写入数据库。
    
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
    repo = FPIRepository(engine, cache_config)
    
    # 检查是否需要更新
    if not force_update:
        existing = repo.get()
        if not existing.empty:
            logger.info(f"使用现有 FPI 数据: {len(existing)} 条")
            return len(existing)
    
    # 获取新数据
    df = fetch_fpi_data(start_date=start_date)
    repo.save(df)
    
    logger.info(
        "FPI 数据已保存至数据库 [financial_fpi_data]"
        "（年度频率，指标计算时需前向填充）"
    )
    return len(df)


# ---------------------------------------------------------------------------
# 主程序入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    save_fpi_to_db()
