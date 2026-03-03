"""
土地数据获取模块 (优化版)
包含：
1. 土地溢价率 (Premium Rate)
2. 土地成交均价 (元/㎡) - 新增

LPR 双轨制验证：
- 土地溢价率回升 AND 土地均价斜率 > 0
"""
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from typing import Optional, List


class LandDataFetcher:
    """
    土地数据获取器
    
    数据来源：
    - 土拍网 (tupai.com)
    - 东方财富
    - 克尔瑞 (CRIC)
    - 公开数据整合
    """
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
    def fetch_land_transaction_data(
        self, 
        start_date: str = "2015-01-01",
        end_date: str = None,
        city: str = "全国"
    ) -> Optional[pd.DataFrame]:
        """
        获取土地成交数据
        
        Returns:
            DataFrame with columns:
            - date: 日期
            - city: 城市
            - land_area: 成交面积 (万㎡)
            - land_count: 成交数量 (宗)
            - premium_rate: 溢价率 (%)
            - land_price: 成交均价 (元/㎡)
            - total_value: 总成交金额 (亿元)
            - source: 数据来源
        """
        
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 尝试从真实API获取 (此处使用模拟数据作为fallback)
        df = self._fetch_from_public_data(start_date, end_date)
        
        return df
    
    def _fetch_from_public_data(
        self, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        基于公开数据生成土地数据 (模拟)
        
        实际项目应接入：
        - 土拍网 API
        - 东方财富 土拍数据
        - 克尔瑞土拍数据库
        """
        
        dates = pd.date_range(start=start_date, end=end_date, freq='ME')
        n = len(dates)
        
        # 1. 土地溢价率趋势
        premium_rates = []
        for i, date in enumerate(dates):
            year, month = date.year, date.month
            
            # 2016-2021 高溢价期，之后下降
            if year <= 2016:
                base = 45 - (2016 - year) * 2
            elif year <= 2021:
                base = 35 - (year - 2017) * 3
            else:
                base = 15 - (year - 2022) * 3
            
            seasonal = 8 * np.sin(2 * np.pi * month / 12)
            noise = np.random.normal(0, 3)
            
            premium = max(base + seasonal + noise, 0)
            premium_rates.append(premium)
        
        # 2. 土地成交面积趋势
        base_area = 5000  # 万㎡
        land_areas = []
        for i, date in enumerate(dates):
            year = date.year
            
            if year <= 2020:
                trend = base_area + year * 100
            else:
                trend = base_area + 2000 - (year - 2020) * 300
            
            noise = np.random.normal(0, 200)
            land_areas.append(max(trend + noise, 500))
        
        # 3. 土地成交均价 (元/㎡) - 关键新增
        land_prices = []
        for i, date in enumerate(dates):
            year, month = date.year, date.month
            
            # 均价持续上涨，直到2021年后涨幅放缓
            if year <= 2021:
                base = 3000 + year * 200            else:
                base = 720
0 + (year - 2022) * 100
            
            seasonal = 200 * np.sin(2 * np.pi * month / 12)
            noise = np.random.normal(0, 100)
            
            price = max(base + seasonal + noise, 2000)
            land_prices.append(price)
        
        # 4. 成交数量
        land_counts = [int(area / 50) for area in land_areas]
        
        # 5. 总成交金额
        total_values = [
            area * price / 10000  # 亿元
            for area, price in zip(land_areas, land_prices)
        ]
        
        df = pd.DataFrame({
            'date': dates,
            'city': '全国',
            'land_area': land_areas,
            'land_count': land_counts,
            'premium_rate': premium_rates,
            'land_price': land_prices,  # 元/㎡
            'total_value': total_values,  # 亿元
            'source': 'simulation'
        })
        
        return df
    
    def calculate_lpr_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 LPR 信号
        
        双轨制验证：
        1. 溢价率回升: MA6回升 或 斜率>0
        2. 均价斜率 > 0
        """
        
        result = df.copy()
        
        # 溢价率6个月均值
        result['premium_6ma'] = result['premium_rate'].rolling(6, min_periods=3).mean()
        
        # 溢价率斜率
        result['premium_slope'] = result['premium_rate'].rolling(6, min_periods=3).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
            raw=True
        )
        
        # 均价斜率 (关键!)
        result['price_slope'] = result['land_price'].rolling(6, min_periods=3).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
            raw=True
        )
        
        # 溢价率变化
        result['premium_change'] = result['premium_rate'].diff()
        
        # 双轨制信号
        condition1 = (result['premium_slope'] > 0) | (result['premium_rate'] > result['premium_6ma'])
        condition2 = result['price_slope'] > 0
        
        result['I_LPR'] = (condition1 & condition2).astype(int)
        
        # 信号描述
        result['LPR_signal_desc'] = result.apply(
            lambda x: '双轨满足' if x['I_LPR'] == 1 else (
                '仅溢价率回升' if x['premium_slope'] > 0 or x['premium_rate'] > x['premium_6ma'] else (
                    '仅均价上涨' if x['price_slope'] > 0 else '均未满足'
                )
            ),
            axis=1
        )
        
        return result


def fetch_land_data(start_date: str = "2015-01-01", end_date: str = None) -> pd.DataFrame:
    """
    对外接口：获取土地数据
    """
    fetcher = LandDataFetcher()
    df = fetcher.fetch_land_transaction_data(start_date, end_date)
    df = fetcher.calculate_lpr_signals(df)
    return df


if __name__ == "__main__":
    df = fetch_land_data()
    print(df.tail(12))
    print("\n信号统计:")
    print(df['LPR_signal_desc'].value_counts())
