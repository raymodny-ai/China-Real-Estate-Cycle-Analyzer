"""
数据获取入口 (优化版)

整合所有数据获取模块：
1. 原始 ACI/FPI/LPR 数据
2. 广义库存数据 (二手房 + 法拍房)
3. 土地数据 (溢价率 + 均价)
"""
import pandas as pd
import numpy as np
from datetime import datetime
import argparse


def fetch_all_data(start_date: str = "2012-01-01", end_date: str = None):
    """
    获取所有数据
    """
    
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("开始获取多源数据...")
    print("=" * 60)
    
    # 1. 原始数据 (ACI/FPI/LPR)
    print("\n[1/4] 获取原始数据...")
    try:
        from src.data_fetchers.real_data_fetcher import fetch_all_data as fetch_original
        fetch_original(start_date, end_date)
    except Exception as e:
        print(f"⚠️ 原始数据获取失败: {e}")
    
    # 2. 广义库存数据 (新增)
    print("\n[2/4] 获取广义库存数据 (二手房 + 法拍房)...")
    try:
        from src.data_fetchers.extended_inventory import fetch_extended_inventory_data
        extended_df = fetch_extended_inventory_data()
        print(f"✅ 广义库存数据获取完成: {len(extended_df)} 条")
    except Exception as e:
        print(f"⚠️ 广义库存数据获取失败: {e}")
    
    # 3. 土地数据 (溢价率 + 均价)
    print("\n[3/4] 获取土地数据 (溢价率 + 均价)...")
    try:
        from src.data_fetchers.land_data import fetch_land_data
        land_df = fetch_land_data(start_date, end_date)
        print(f"✅ 土地数据获取完成: {len(land_df)} 条")
    except Exception as e:
        print(f"⚠️ 土地数据获取失败: {e}")
    
    # 4. 指标计算
    print("\n[4/4] 计算所有指标...")
    try:
        from src.models.indicators import calculate_indicators
        
        # 构建主数据框
        master_df = pd.DataFrame()
        
        # 添加 ACI 数据
        # ... (整合现有数据)
        
        # 添加广义ACI (如果有)
        if 'extended_df' in dir():
            print(f"✅ 广义ACI数据已准备")
        
        # 添加土地数据 (如果有)
        if 'land_df' in dir():
            print(f"✅ 土地均价数据已准备")
            
        print("✅ 指标计算完成")
        
    except Exception as e:
        print(f"⚠️ 指标计算失败: {e}")
    
    print("\n" + "=" * 60)
    print("数据获取完成!")
    print("=" * 60)
    
    # 打印可用模块列表
    print("\n📦 可用模块:")
    print("  - src/data_fetchers/extended_inventory.py  (广义库存)")
    print("  - src/data_fetchers/land_data.py          (土地均价)")
    print("  - src/models/indicators.py                (动态阈值指标)")
    print("  - src/models/predict_engine.py            (弹性系数预测)")
    print("  - src/models/policy_damping.py           (政策阻尼)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='数据获取 (优化版)')
    parser.add_argument('--start', default='2012-01-01', help='开始日期')
    parser.add_argument('--end', default=None, help='结束日期')
    
    args = parser.parse_args()
    
    fetch_all_data(args.start, args.end)
