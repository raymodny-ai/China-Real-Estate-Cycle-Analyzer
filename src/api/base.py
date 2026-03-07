"""
API 客户端基类与数据源接口
提供统一的数据获取抽象层，便于接入多种真实数据源。
"""
from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据源配置
# ---------------------------------------------------------------------------

@dataclass
class DataSourceConfig:
    """数据源配置数据类"""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit: int = 60  # 每分钟请求数

    @classmethod
    def from_env(cls, prefix: str) -> "DataSourceConfig":
        """从环境变量加载配置"""
        return cls(
            name=os.getenv(f"{prefix}_NAME", "unknown"),
            api_key=os.getenv(f"{prefix}_API_KEY"),
            base_url=os.getenv(f"{prefix}_BASE_URL"),
            timeout=int(os.getenv(f"{prefix}_TIMEOUT", "30")),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", "3")),
        )


# ---------------------------------------------------------------------------
# 抽象数据源基类
# ---------------------------------------------------------------------------

class DataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """延迟初始化请求会话"""
        if self._session is None:
            self._session = requests.Session()
            if self.config.api_key:
                self._session.headers.update({"Authorization": f"Bearer {self.config.api_key}"})
        return self._session

    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        """获取数据的抽象方法，子类必须实现"""
        pass

    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------------------------------------------------------------------------
# 国家统计局数据源
# ---------------------------------------------------------------------------

class NBSDataSource(DataSource):
    """
    国家统计局数据接口
    API 文档: https://data.stats.gov.cn/api/
    
    注意：需要申请 API Key，免费额度有限
    """
    
    # 常用统计指标代码
    INDICATOR_CODES = {
        "sales_area": "E0101",       # 商品房销售面积
        "inventory_area": "E0102",  # 商品房待售面积
        "investment": "E0103",       # 房地产开发投资
        "price_index": "E0104",     # 房价指数
    }

    def __init__(self, config: Optional[DataSourceConfig] = None):
        if config is None:
            config = DataSourceConfig.from_env("NBS")
            config.base_url = config.base_url or "https://data.stats.gov.cn"
        super().__init__(config)
        self.name = "nbs"  # 添加 name 属性

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch(
        self,
        indicator: str,
        start_date: str,
        end_date: str,
        region: str = "全国",
    ) -> pd.DataFrame:
        """
        获取国家统计局数据
        
        Args:
            indicator: 指标代码或名称
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            region: 地区名称
            
        Returns:
            包含数据的 DataFrame
        """
        if not self.config.api_key:
            logger.warning("未配置 NBS API Key，使用模拟数据")
            return self._generate_mock_data(indicator, start_date, end_date)

        code = self.INDICATOR_CODES.get(indicator, indicator)
        
        params = {
            "method": "queryData",
            "dbcode": "fsnd",
            "rowcode": "reg",
            "colcode": "sj",
            "wds": [
                {"wdcode": "zb", "valuecode": code},
                {"wdcode": "sj", "valuecode": f"{start_date[:4]}-{end_date[:4]}"},
            ],
            "k1": int(datetime.now().timestamp() * 1000),
        }

        try:
            response = self.session.get(
                f"{self.config.base_url}/easyquery",
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            return self._parse_nbs_response(data, indicator)
            
        except requests.RequestException as e:
            logger.error(f"国家统计局 API 请求失败: {e}")
            return self._generate_mock_data(indicator, start_date, end_date)

    def _parse_nbs_response(self, data: dict, indicator: str) -> pd.DataFrame:
        """解析国家统计局响应数据"""
        # TODO: 根据实际 API 响应格式实现
        logger.warning("NBS 响应解析未完全实现，返回空数据")
        return pd.DataFrame()

    def _generate_mock_data(
        self,
        indicator: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """生成模拟数据（当 API 不可用时）"""
        dates = pd.date_range(start=start_date, end=end_date, freq="ME")
        n = len(dates)
        
        if indicator == "sales_area":
            data = 12000 + 100 * np.arange(n) - 0.8 * np.arange(n) ** 2
            data += 1500 * np.sin(2 * np.pi * np.arange(n) / 12)
            data = np.maximum(data, 2000)
            return pd.DataFrame({"date": dates, "sales_area": data})
        
        elif indicator == "inventory_area":
            inventory = np.zeros(n)
            inventory[0] = 60000
            for i in range(1, n):
                completions = 11000 + 30 * i
                inventory[i] = inventory[i - 1] + completions - data[i - 1] if i > 0 else inventory[0]
                inventory[i] = max(inventory[i], 10000)
            return pd.DataFrame({"date": dates, "inventory_area": inventory})
        
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# 东方财富 Choice 数据源
# ---------------------------------------------------------------------------

class ChoiceDataSource(DataSource):
    """
    东方财富 Choice 金融终端数据接口
    
    注意：需要付费订阅，仅支持 Windows 平台
    建议在服务器上部署使用
    """

    def __init__(self, config: Optional[DataSourceConfig] = None):
        if config is None:
            config = DataSourceConfig.from_env("CHOICE")
            config.base_url = config.base_url or "http://localhost:8765"
        super().__init__(config)

    def fetch_fpi(
        self,
        tickers: list[str],
        start_year: int,
        end_year: int,
    ) -> pd.DataFrame:
        """
        获取房企资金流数据
        
        Args:
            tickers: 股票代码列表，如 ['000002.SZ', '600048.SS']
            start_year: 开始年份
            end_year: 结束年份
            
        Returns:
            年度净融资现金流 DataFrame
        """
        if not self.config.api_key:
            logger.warning("未配置 Choice API，使用模拟数据")
            return self._generate_mock_fpi(start_year, end_year)

        # TODO: 实现 Choice API 调用
        # import Choice as cx
        # with cx.init():
        #     df = cx.FinancialAnalysis.FinanceCashFlow(tickers=tickers)
        
        return self._generate_mock_fpi(start_year, end_year)

    def fetch(self, **kwargs) -> pd.DataFrame:
        """实现抽象方法，默认调用 fetch_fpi"""
        return self._generate_mock_fpi(2020, 2024)

    def _generate_mock_fpi(self, start_year: int, end_year: int) -> pd.DataFrame:
        """生成模拟 FPI 数据"""
        years = list(range(start_year, end_year + 1))
        n = len(years)
        
        # 模拟净融资现金流趋势：2013-2017 高正值，2018-2020 收紧，2021-今 负值
        net_financing = 80000 - 8000 * np.arange(n)
        net_financing = net_financing + np.random.normal(0, 5000, n)
        
        return pd.DataFrame({
            "date": pd.to_datetime([f"{y}-12-31" for y in years]),
            "net_financing_cash_flow": net_financing,
            "ticker": "SECTOR_AGGREGATE",
            "data_frequency": "ANNUAL",
        })


# ---------------------------------------------------------------------------
# 中指研究院 / CRIC 数据源
# ---------------------------------------------------------------------------

class CRICDataSource(DataSource):
    """
    克而瑞（CRIC）数据接口
    
    提供土地交易数据、房价数据等
    注意：需要付费订阅
    """

    def __init__(self, config: Optional[DataSourceConfig] = None):
        if config is None:
            config = DataSourceConfig.from_env("CRIC")
            config.base_url = config.base_url or "https://api.cric.com"
        super().__init__(config)

    def fetch_land(
        self,
        city: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取土地交易数据
        
        Args:
            city: 城市名称（可选）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            土地交易 DataFrame
        """
        if not self.config.api_key:
            logger.warning("未配置 CRIC API，使用模拟数据")
            return self._generate_mock_land(start_date, end_date)

        # TODO: 实现 CRIC API 调用
        
        return self._generate_mock_land(start_date, end_date)

    def fetch(self, **kwargs) -> pd.DataFrame:
        """实现抽象方法，默认调用 fetch_land"""
        return self._generate_mock_land("2020-01-01", "2024-12-31")

    def _generate_mock_land(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """生成模拟土地数据"""
        if start_date is None:
            start_date = "2013-01-01"
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        dates = pd.date_range(start=start_date, end=end_date, freq="ME")
        n = len(dates)
        t = np.arange(n)
        
        # 溢价率：从约 25% 线性下行
        premium_rate = 25 - 0.25 * t + 3 * np.sin(2 * np.pi * t / 12)
        premium_rate = np.maximum(premium_rate, 0.0)
        
        # 成交面积
        land_volume = 1200 - 8 * t
        land_volume = np.maximum(land_volume, 100.0)
        
        return pd.DataFrame({
            "date": dates,
            "premium_rate": premium_rate,
            "land_volume": land_volume,
        })


# ---------------------------------------------------------------------------
# 数据源工厂
# ---------------------------------------------------------------------------

class DataSourceFactory:
    """数据源工厂类"""
    
    _sources: dict[str, type[DataSource]] = {
        "nbs": NBSDataSource,
        "choice": ChoiceDataSource,
        "cric": CRICDataSource,
    }
    
    @classmethod
    def create(cls, source_type: str, **kwargs) -> DataSource:
        """创建数据源实例"""
        source_class = cls._sources.get(source_type.lower())
        if source_class is None:
            raise ValueError(f"未知数据源类型: {source_type}")
        return source_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, source_class: type[DataSource]):
        """注册新的数据源"""
        cls._sources[name.lower()] = source_class


# ---------------------------------------------------------------------------
# 统一数据获取接口
# ---------------------------------------------------------------------------

@dataclass
class FetchResult:
    """数据获取结果"""
    success: bool
    data: pd.DataFrame
    source: str
    error: Optional[str] = None
    fetch_time: datetime = field(default_factory=datetime.now)


def fetch_with_fallback(
    source_type: str,
    fetch_func: str,
    **kwargs,
) -> FetchResult:
    """
    带降级策略的数据获取
    
    优先使用真实数据源，失败时自动降级到模拟数据
    
    Args:
        source_type: 数据源类型 (nbs/choice/cric)
        fetch_func: 获取方法名
        **kwargs: 传递给获取方法的参数
        
    Returns:
        FetchResult 对象
    """
    try:
        source = DataSourceFactory.create(source_type)
        method = getattr(source, fetch_func)
        data = method(**kwargs)
        return FetchResult(
            success=True,
            data=data,
            source=source_type,
        )
    except Exception as e:
        logger.error(f"数据获取失败 [{source_type}.{fetch_func}]: {e}")
        
        # 降级到模拟数据
        try:
            source = DataSourceFactory.create(source_type)
            mock_method = getattr(source, f"_generate_mock_{fetch_func.split('_')[0]}")
            # 提取日期参数
            start = kwargs.get("start_date") or kwargs.get("start_year", 2013)
            end = kwargs.get("end_date") or kwargs.get("end_year", 2024)
            data = mock_method(start, end)
            return FetchResult(
                success=True,
                data=data,
                source=f"{source_type}_mock",
                error=str(e),
            )
        except Exception as mock_e:
            return FetchResult(
                success=False,
                data=pd.DataFrame(),
                source=source_type,
                error=f"真实数据和模拟数据均失败: {e}, {mock_e}",
            )


# ---------------------------------------------------------------------------
# 导入依赖
# ---------------------------------------------------------------------------

import numpy as np
