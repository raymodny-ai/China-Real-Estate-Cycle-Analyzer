"""
土地市场数据客户端 - Land Client
提供土地溢价拍买率等数据。
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

class LandClient:
    """土地成交数据获取客户端"""
    
    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
        except ImportError:
            self.available = False
            logger.warning("akshare 未安装，LandClient 可能无法获取真实数据。")

    def fetch_premium_data(
        self, start_date: str = "2013-01-01", end_date: Optional[str] = None, city: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取全国/城市土地成交溢价率和面积数据
        """
        if not self.available:
            return pd.DataFrame()
            
        try:
            # 调用 akshare 的 land_data 或 land_city_data
            if city:
                df = self.ak.land_city_data(city=city)
            else:
                df = self.ak.land_data()
                
            if df.empty:
                return pd.DataFrame()
                
            date_col = next((c for c in ["成交日期", "日期", "月份"] if c in df.columns), None)
            if not date_col:
                return pd.DataFrame()
                
            df["date"] = pd.to_datetime(df[date_col])
            
            if start_date:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["date"] <= pd.to_datetime(end_date)]
                
            premium_col = next((c for c in ["溢价率", "土地溢价率", "溢价率(%)", "溢价率(百分比)"] if c in df.columns), None)
            volume_col = next((c for c in ["成交面积", "土地成交面积", "成交量"] if c in df.columns), None)
            
            if premium_col:
                df["premium_rate"] = pd.to_numeric(df[premium_col], errors="coerce")
            if volume_col:
                df["land_volume"] = pd.to_numeric(df[volume_col], errors="coerce")
                
            cols_to_keep = ["date"]
            if "premium_rate" in df.columns: cols_to_keep.append("premium_rate")
            if "land_volume" in df.columns: cols_to_keep.append("land_volume")
            
            res = df[cols_to_keep].dropna().sort_values("date")
            # 处理可能的无穷大或负值
            if "premium_rate" in res.columns:
                res["premium_rate"] = res["premium_rate"].clip(lower=0)
            return res
            
        except Exception as e:
            logger.error(f"LandClient 获取土地数据失败: {e}")
            return pd.DataFrame()
