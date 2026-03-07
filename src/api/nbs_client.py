"""
国家统计局 (NBS) 数据客户端 - NBS Client
提供 ACI 相关的基础数据：商品房销售面积，待售面积。
底层使用 akshare.macro_china_real_estate 或其他类似接口，并做好异常和类型处理。
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

class NBSClient:
    """国家统计局数据获取客户端"""
    
    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
        except ImportError:
            self.available = False
            logger.warning("akshare 未安装，NBSClient 可能无法获取真实数据。")

    def fetch_real_estate_data(
        self, start_date: str = "2013-01-01", end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取全国房地产销售和库存面积数据
        """
        if not self.available:
            return pd.DataFrame()
            
        try:
            # macro_china_real_estate 返回包含 '月份', '商品房销售面积', '商品房待售面积' 的 DataFrame
            df = self.ak.macro_china_real_estate()
            if df.empty:
                return pd.DataFrame()
                
            if "月份" in df.columns:
                df["date"] = pd.to_datetime(df["月份"])
            elif "日期" in df.columns:
                df["date"] = pd.to_datetime(df["日期"])
            else:
                return pd.DataFrame()
                
            if start_date:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df["date"] <= pd.to_datetime(end_date)]
                
            rename_map = {}
            if "商品房销售面积" in df.columns:
                rename_map["商品房销售面积"] = "sales_area"
            if "商品房待售面积" in df.columns:
                rename_map["商品房待售面积"] = "inventory_area"
                
            df = df.rename(columns=rename_map)
            
            # 尝试转换为数值型
            for col in ["sales_area", "inventory_area"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    
            cols_to_keep = ["date"] + [c for c in ["sales_area", "inventory_area"] if c in df.columns]
            return df[cols_to_keep].dropna().sort_values("date")
            
        except Exception as e:
            logger.error(f"NBSClient 获取房地产数据失败: {e}")
            return pd.DataFrame()
