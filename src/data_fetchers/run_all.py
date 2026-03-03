"""
数据获取主程序
支持：
1. 模拟数据 (默认): python src/data_fetchers/run_all.py
2. 真实数据: python src/data_fetchers/run_all.py --real
3. 租售比数据: python src/data_fetchers/run_all.py --rent
"""
import sys
import os
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def run_simulation():
    """运行模拟数据生成"""
    from src.data_fetchers.macro_data import save_aci_to_db
    from src.data_fetchers.financial_data import save_fpi_to_db
    from src.data_fetchers.land_data import save_lpr_to_db
    
    print("Running simulation data fetchers...")
    save_aci_to_db()
    save_fpi_to_db()
    save_lpr_to_db()
    print("Simulation data fetch completed.")

def run_real_data():
    """运行真实数据获取"""
    try:
        from src.data_fetchers.real_data_fetcher import (
            fetch_all_data,
            fetch_aci_data,
            fetch_fpi_data,
            fetch_lpr_data
        )
        
        print("Fetching real data from multiple sources...")
        fetch_all_data()
        print("Real data fetch completed.")
        
    except ImportError as e:
        print(f"Error: {e}")
        print("请确保已正确配置数据源")

def run_rent_data():
    """运行租售比数据获取"""
    try:
        from src.data_fetchers.rent_price_ratio import (
            save_rent_ratio_to_db,
            save_rent_ratio_by_city_to_db
        )
        
        print("Fetching rent price ratio data...")
        save_rent_ratio_to_db()
        save_rent_ratio_by_city_to_db()
        print("Rent price ratio data fetch completed.")
        
    except ImportError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='数据获取程序')
    parser.add_argument('--real', action='store_true', 
                       help='使用真实数据源（默认使用模拟数据）')
    parser.add_argument('--rent', action='store_true',
                       help='获取租售比数据')
    parser.add_argument('--source', type=str, default='all',
                       choices=['all', 'aci', 'land', 'fpi', 'rent'],
                       help='指定获取的数据类型')
    parser.add_argument('--cities', type=str, default='',
                       help='租售比数据: 城市列表(逗号分隔)')
    
    args = parser.parse_args()
    
    if args.rent or args.source == 'rent':
        # 只获取租售比数据
        if args.cities:
            cities = args.cities.split(',')
            from src.data_fetchers.rent_price_ratio import save_rent_ratio_by_city_to_db
            save_rent_ratio_by_city_to_db(cities)
        else:
            run_rent_data()
    elif args.real:
        run_real_data()
    else:
        run_simulation()
