"""
数据仓储层 — Data Repository
提供统一的数据存取接口，支持缓存和增量更新
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Callable

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 缓存配置
# ---------------------------------------------------------------------------

@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    ttl_minutes: int = 60  # 缓存有效期
    cache_dir: str = "data/cache"
    max_size_mb: int = 100


# ---------------------------------------------------------------------------
# 数据仓储基类
# ---------------------------------------------------------------------------

class DataRepository:
    """
    数据仓储抽象类
    定义数据存取的标准接口
    """
    
    def __init__(
        self,
        db_engine,
        cache_config: Optional[CacheConfig] = None,
    ):
        self.db_engine = db_engine
        self.cache_config = cache_config or CacheConfig()
        self._cache_dir = Path(self.cache_config.cache_dir)
        if self.cache_config.enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    # ------------------------------------------------------------------------
    # 抽象方法 (子类必须实现)
    # ------------------------------------------------------------------------
    
    def get_table_name(self) -> str:
        """返回数据库表名"""
        raise NotImplementedError
    
    def get_primary_key(self) -> list[str]:
        """返回主键列名"""
        raise NotImplementedError
    
    def get_date_column(self) -> str:
        """返回日期列名"""
        raise NotImplementedError
    
    # ------------------------------------------------------------------------
    # 通用方法
    # ------------------------------------------------------------------------
    
    def _get_cache_key(self, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps(kwargs, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self._cache_dir / f"{self.get_table_name()}_{key}.parquet"
    
    def get_cached(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Optional[pd.DataFrame]:
        """
        获取缓存数据
        
        Returns:
            缓存数据或 None（无缓存/过期）
        """
        if not self.cache_config.enabled:
            return None
            
        cache_key = self._get_cache_key(
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        # 检查过期
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if (datetime.now() - mtime) > timedelta(minutes=self.cache_config.ttl_minutes):
            logger.debug(f"缓存已过期: {cache_path}")
            return None
        
        try:
            df = pd.read_parquet(cache_path)
            logger.debug(f"读取缓存: {cache_path}")
            return df
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
    
    def set_cached(self, df: pd.DataFrame, **kwargs):
        """保存数据到缓存"""
        if not self.cache_config.enabled or df.empty:
            return
            
        cache_key = self._get_cache_key(**kwargs)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            df.to_parquet(cache_path, index=False)
            logger.debug(f"写入缓存: {cache_path}")
        except Exception as e:
            logger.warning(f"写入缓存失败: {e}")
    
    def get(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        获取数据（带缓存）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存
            
        Returns:
            DataFrame
        """
        # 尝试缓存
        if use_cache:
            cached = self.get_cached(start_date, end_date)
            if cached is not None:
                return self._filter_by_date(cached, start_date, end_date)
        
        # 从数据库加载
        df = self._load_from_db(start_date, end_date)
        
        # 缓存结果
        if use_cache and not df.empty:
            self.set_cached(df, start_date=start_date, end_date=end_date)
        
        return df
    
    def _load_from_db(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """从数据库加载数据"""
        query = f"SELECT * FROM {self.get_table_name()}"
        conditions = []
        
        if start_date:
            conditions.append(f"{self.get_date_column()} >= '{start_date}'")
        if end_date:
            conditions.append(f"{self.get_date_column()} <= '{end_date}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        return pd.read_sql(query, con=self.db_engine)
    
    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """按日期过滤 DataFrame"""
        if df.empty or self.get_date_column() not in df.columns:
            return df
        
        df = df.copy()
        df[self.get_date_column()] = pd.to_datetime(df[self.get_date_column()])
        
        mask = pd.Series(True, index=df.index)
        if start_date:
            mask &= df[self.get_date_column()] >= pd.to_datetime(start_date)
        if end_date:
            mask &= df[self.get_date_column()] <= pd.to_datetime(end_date)
        
        return df[mask]
    
    def save(self, df: pd.DataFrame, if_exists: str = "replace"):
        """保存数据到数据库"""
        df.to_sql(
            self.get_table_name(),
            con=self.db_engine,
            if_exists=if_exists,
            index=False,
        )
        logger.info(f"数据已保存到 {self.get_table_name()}, {len(df)} 条记录")
    
    def get_latest_date(self) -> Optional[datetime]:
        """获取最新数据日期"""
        query = f"SELECT MAX({self.get_date_column()}) as max_date FROM {self.get_table_name()}"
        try:
            result = pd.read_sql(query, con=self.db_engine)
            if not result.empty and result.iloc[0]["max_date"]:
                return pd.to_datetime(result.iloc[0]["max_date"])
        except Exception as e:
            logger.warning(f"获取最新日期失败: {e}")
        return None
    
    def has_new_data(self, source_date: datetime) -> bool:
        """检查是否有新数据需要更新"""
        latest = self.get_latest_date()
        if latest is None:
            return True
        return source_date > latest


# ---------------------------------------------------------------------------
# 具体仓储实现
# ---------------------------------------------------------------------------

class ACIRepository(DataRepository):
    """ACI 数据仓储"""
    
    def get_table_name(self) -> str:
        return "macro_aci_data"
    
    def get_primary_key(self) -> list[str]:
        return ["date"]
    
    def get_date_column(self) -> str:
        return "date"


class FPIRepository(DataRepository):
    """FPI 数据仓储"""
    
    def get_table_name(self) -> str:
        return "financial_fpi_data"
    
    def get_primary_key(self) -> list[str]:
        return ["date", "ticker"]
    
    def get_date_column(self) -> str:
        return "date"


class LPRRepository(DataRepository):
    """LPR 数据仓储"""
    
    def get_table_name(self) -> str:
        return "land_lpr_data"
    
    def get_primary_key(self) -> list[str]:
        return ["date"]
    
    def get_date_column(self) -> str:
        return "date"


class CIRepository(DataRepository):
    """CI 指数仓储"""
    
    def get_table_name(self) -> str:
        return "model_ci_index"
    
    def get_primary_key(self) -> list[str]:
        return ["date"]
    
    def get_date_column(self) -> str:
        return "date"


# ---------------------------------------------------------------------------
# 仓储工厂
# ---------------------------------------------------------------------------

class RepositoryFactory:
    """仓储工厂"""
    
    _repositories: dict[str, type[DataRepository]] = {
        "aci": ACIRepository,
        "fpi": FPIRepository,
        "lpr": LPRRepository,
        "ci": CIRepository,
    }
    
    @classmethod
    def create(
        cls,
        repo_type: str,
        db_engine,
        cache_config: Optional[CacheConfig] = None,
    ) -> DataRepository:
        """创建仓储实例"""
        repo_class = cls._repositories.get(repo_type.lower())
        if repo_class is None:
            raise ValueError(f"未知仓储类型: {repo_type}")
        return repo_class(db_engine, cache_config)
