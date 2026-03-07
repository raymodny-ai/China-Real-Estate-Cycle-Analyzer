"""
债券与融资数据客户端 - Bond Client
提供房企融资资金链等相关数据。
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

class BondClient:
    """融资与债券数据获取客户端"""
    
    def __init__(self):
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
        except ImportError:
            self.available = False
            logger.warning("akshare 未安装，BondClient 可能无法获取真实数据。")

    def fetch_financing_data(
        self, start_year: int = 2013, end_year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        获取行业融资到位资金/净融资现金流
        注：若 akshare 缺乏直接的房地产净融资流数据，可使用房地产开发投资中的“本年到位资金”近似替代。
        """
        if not self.available:
            return pd.DataFrame()
            
        try:
            # 尝试获取房地产投资资金数据
            df = self.ak.macro_china_real_estate_investment()
            if df.empty:
                return pd.DataFrame()
                
            # df 可能包含 '时间', '房地产开发投资_本年到位资金' 等相关字段
            time_col = next((c for c in ["时间", "月份", "日期"] if c in df.columns), None)
            if not time_col:
                return pd.DataFrame()
                
            df["date"] = pd.to_datetime(df[time_col])
            
            # 使用年度或月度的数据
            # 如果是月度，我们提取对应的净融资或到位资金
            money_col = next((c for c in df.columns if "到位资金" in c or "资金来源" in c), None)
            
            if money_col:
                df["net_financing_cash_flow"] = pd.to_numeric(df[money_col], errors="coerce")
            else:
                # 寻找其他可能表示资金流的数值列（如果是模拟后降级）
                return pd.DataFrame()
                
            if start_year:
                df = df[df["date"].dt.year >= start_year]
            if end_year:
                df = df[df["date"].dt.year <= end_year]
                
            df["ticker"] = "SECTOR_AGGREGATE"
            df["data_frequency"] = "MONTHLY"
            
            cols_to_keep = ["date", "net_financing_cash_flow", "ticker", "data_frequency"]
            return df[cols_to_keep].dropna().sort_values("date")
            
        except Exception as e:
            logger.error(f"BondClient 获取融资数据失败: {e}")
            return pd.DataFrame()
