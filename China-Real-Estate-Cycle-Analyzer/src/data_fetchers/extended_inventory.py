"""
广义库存数据获取模块
扩充 ACI 数据源：二手房挂牌量 + 法拍房挂牌量

针对"中共数据不可信"与"高库存"节点：
- 贝壳/链家 二手房挂牌量
- 阿里法拍房 挂牌量
"""
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time


class ExtendedInventoryFetcher:
    """
    广义库存数据获取器
    
    广义ACI = (新房可售面积 + 二手房挂牌量折算面积 + 法拍房挂牌量) / 综合去化流速
    """
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.session = requests.Session()
        
    def fetch_secondhand_listings(self, city: str = "全国") -> Optional[pd.DataFrame]:
        """
        获取贝壳/链家 二手房挂牌量
        
        注意：贝壳反爬严格，此处使用模拟数据作为fallback
        实际部署需要接入贝壳API或第三方数据源
        
        Returns:
            DataFrame with columns: [date, city, listings, source]
        """
        try:
            # 方法1: 尝试第三方数据API (如选房网、安居客等)
            # 此处使用公开数据模拟
            # 实际项目可壳数据API、房价接入: 贝网数据等
            
            dates = pd.date_range(start="2020-01-01", end=datetime.now().strftime("%Y-%m-%d"), freq='ME')
            n = len(dates)
            
            # 模拟数据：全国二手房挂牌量趋势
            # 2020-2023 持续上升，2023年底开始下降
            base_listings = 100  # 万套
            
            listings = []
            for i, date in enumerate(dates):
                year = date.year
                month = date.month
                
                if year == 2020:
                    trend = 100 + i * 2
                elif year == 2021:
                    trend = 150 + (i - 12) * 3
                elif year == 2022:
                    trend = 200 + (i - 24) * 2
                elif year == 2023:
                    trend = 240 + (i - 36) * 1.5
                else:
                    trend = 260 - (i - 48) * 3
                
                # 季节性波动
                seasonal = 10 * np.sin(2 * np.pi * month / 12)
                noise = np.random.normal(0, 5)
                
                listings.append(max(trend + seasonal + noise, 80))
            
            df = pd.DataFrame({
                'date': dates,
                'city': city,
                'secondhand_listings': listings,  # 万套
                'source': 'simulation'  # 实际部署需替换为真实数据源
            })
            
            print(f"✅ 二手房挂牌量数据生成完成，共 {len(df)} 条")
            return df
            
        except Exception as e:
            print(f"❌ 二手房数据获取失败: {e}")
            return None
    
    def fetch_auction_listings(self, city: str = "全国") -> Optional[pd.DataFrame]:
        """
        获取阿里法拍房 挂牌量
        
        阿里法拍数据来源：
        - 阿里拍卖平台 (https://sf.taobao.com)
        - 第三方数据聚合
        
        Returns:
            DataFrame with columns: [date, city, auction_count, total_value, source]
        """
        try:
            dates = pd.date_range(start="2020-01-01", end=datetime.now().strftime("%Y-%m-%d"), freq='ME')
            n = len(dates)
            
            # 法拍房数量趋势
            # 2020-2022 快速增长，2023趋于稳定
            base_count = 20  # 万套
            
            counts = []
            values = []  # 亿元
            
            for i, date in enumerate(dates):
                year = date.year
                month = date.month
                
                if year == 2020:
                    trend = 20 + i * 1.5
                elif year == 2021:
                    trend = 50 + (i - 12) * 2
                elif year == 2022:
                    trend = 100 + (i - 24) * 1
                elif year == 2023:
                    trend = 140 + (i - 36) * 0.5
                else:
                    trend = 150 - (i - 48) * 0.3
                
                seasonal = 5 * np.sin(2 * np.pi * month / 12)
                noise = np.random.normal(0, 3)
                
                count = max(trend + seasonal + noise, 10)
                counts.append(count)
                
                # 法拍房总价值 (亿元) = 数量 * 均价
                avg_price = 150  # 万元/套
                values.append(count * avg_price / 10)
            
            df = pd.DataFrame({
                'date': dates,
                'city': city,
                'auction_listings': counts,  # 万套
                'auction_total_value': values,  # 亿元
                'source': 'simulation'  # 实际部署需替换为真实数据源
            })
            
            print(f"✅ 法拍房挂牌量数据生成完成，共 {len(df)} 条")
            return df
            
        except Exception as e:
            print(f"❌ 法拍房数据获取失败: {e}")
            return None
    
    def calculate_extended_aci(
        self, 
        new_house_inventory: pd.DataFrame,
        sales_area: pd.DataFrame,
        secondhand_listings: Optional[pd.DataFrame] = None,
        auction_listings: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        计算广义 ACI (去化周期)
        
        广义ACI = (新房可售面积 + 二手房挂牌量折算面积 + 法拍房挂牌量) / 综合去化流速
        
        折算说明：
        - 二手房挂牌量折算 = 挂牌套数 * 平均套面积(100㎡)
        - 法拍房挂牌量 = 挂牌套数 * 平均套面积(100㎡)
        """
        
        # 合并基础数据
        df = new_house_inventory.copy()
        df = df.merge(sales_area[['date', 'sales_area']], on='date', how='left')
        
        # 新房可售面积 (万㎡)
        df['new_house_inventory'] = df.get('inventory_area', df.get('aci', 30) * df['sales_area'])
        
        # 二手房折算面积 (万㎡)
        avg_unit_area = 100  # ㎡/套
        
        if secondhand_listings is not None:
            secondhand_area = secondhand_listings['secondhand_listings'] * avg_unit_area / 10000  # 万㎡
            secondhand_listings['secondhand_area'] = secondhand_area
            df = df.merge(secondhand_listings[['date', 'secondhand_area']], on='date', how='left')
        else:
            df['secondhand_area'] = 0
            
        # 法拍房面积 (万㎡)
        if auction_listings is not None:
            auction_area = auction_listings['auction_listings'] * avg_unit_area / 10000
            auction_listings['auction_area'] = auction_area
            df = df.merge(auction_listings[['date', 'auction_area']], on='date', how='left')
        else:
            df['auction_area'] = 0
        
        # 广义库存总面积
        df['extended_inventory'] = (
            df['new_house_inventory'].fillna(0) + 
            df['secondhand_area'].fillna(0) + 
            df['auction_area'].fillna(0)
        )
        
        # 综合去化流速 (月均销售面积)
        df['monthly_sales'] = df['sales_area'].rolling(window=3, min_periods=1).mean()
        
        # 广义ACI
        df['aci_extended'] = df['extended_inventory'] / (df['monthly_sales'] + 1)
        
        # 原始ACI (仅新房)
        df['aci_original'] = df.get('aci', df['new_house_inventory'] / (df['monthly_sales'] + 1))
        
        print(f"✅ 广义ACI计算完成: {len(df)} 条记录")
        print(f"   平均广义ACI: {df['aci_extended'].mean():.1f} 个月")
        print(f"   平均原始ACI: {df['aci_original'].mean():.1f} 个月")
        
        return df


def fetch_extended_inventory_data() -> pd.DataFrame:
    """
    对外接口：获取广义库存数据
    """
    fetcher = ExtendedInventoryFetcher()
    
    # 获取二手房数据
    secondhand = fetcher.fetch_secondhand_listings()
    
    # 获取法拍房数据
    auction = fetcher.fetch_auction_listings()
    
    # 获取新房库存数据 (使用 PublicDataSource 作为fallback)
    from src.data_fetchers.real_data_fetcher import PublicDataSource
    public_source = PublicDataSource()
    new_house = public_source.fetch_aci("2020-01-01", datetime.now().strftime("%Y-%m-%d"))
    
    if new_house is None:
        # 模拟数据
        dates = pd.date_range(start="2020-01-01", end=datetime.now().strftime("%Y-%m-%d"), freq='ME')
        new_house = pd.DataFrame({
            'date': dates,
            'inventory_area': np.random.uniform(50000, 80000, len(dates)),
            'sales_area': np.random.uniform(8000, 15000, len(dates))
        })
    
    # 计算广义ACI
    result = fetcher.calculate_extended_aci(
        new_house[['date', 'inventory_area']], 
        new_house[['date', 'sales_area']],
        secondhand,
        auction
    )
    
    return result


if __name__ == "__main__":
    df = fetch_extended_inventory_data()
    print(df.tail())
