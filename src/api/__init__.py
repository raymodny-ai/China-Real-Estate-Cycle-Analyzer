"""
API 模块
提供外部数据源的统一接入接口
"""

from src.api.base import (
    DataSource,
    DataSourceConfig,
    DataSourceFactory,
    FetchResult,
    fetch_with_fallback,
    NBSDataSource,
    ChoiceDataSource,
    CRICDataSource,
)

# 导入免费数据源
try:
    from src.api import akshare
    from src.api import eastmoney
    AKSHARE_AVAILABLE = True
    EASTMONEY_AVAILABLE = True
except ImportError as e:
    AKSHARE_AVAILABLE = False
    EASTMONEY_AVAILABLE = False

__all__ = [
    # 付费数据源
    "DataSource",
    "DataSourceConfig",
    "DataSourceFactory",
    "FetchResult",
    "fetch_with_fallback",
    "NBSDataSource",
    "ChoiceDataSource",
    "CRICDataSource",
    # 免费数据源
    "akshare",
    "eastmoney",
    "AKSHARE_AVAILABLE",
    "EASTMONEY_AVAILABLE",
]
