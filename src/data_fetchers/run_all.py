"""
数据获取主程序
支持：
1. 模拟数据 (默认): python src/data_fetchers/run_all.py
2. 真实数据: python src/data_fetchers/run_all.py --real
3. 租售比数据: python src/data_fetchers/run_all.py --rent
4. LLM智能获取: python src/data_fetchers/run_all.py --llm
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
    """运行真实数据获取 (AKShare优先)"""
    try:
        from src.data_fetchers.real_data_fetcher import fetch_all_data
        print("Fetching real data from multiple sources...")
        print("推荐: pip install akshare 获得最佳体验")
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

def run_llm_data():
    """运行 LLM 智能数据获取"""
    try:
        from src.data_fetchers.llm_data_fetcher import fetch_data_sources_with_llm, generate_collector
        print("=" * 60)
        print("LLM 智能数据获取")
        print("=" * 60)
        print("\n通过大模型智能分析数据来源...")
        
        # 获取所有指标的数据源信息
        result = fetch_data_sources_with_llm()
        
        print("\n✅ 数据源信息获取完成!")
        print("\n建议: 使用 --generate-code 参数生成采集代码")
        
    except ImportError as e:
        print(f"Error: {e}")
        print("请确保已安装依赖: pip install requests")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='数据获取程序')
    parser.add_argument('--real', action='store_true', 
                       help='使用真实数据源（默认使用模拟数据）')
    parser.add_argument('--rent', action='store_true',
                       help='获取租售比数据')
    parser.add_argument('--llm', action='store_true',
                       help='使用 LLM 智能获取数据源信息')
    parser.add_argument('--source', type=str, default='all',
                       choices=['all', 'aci', 'land', 'fpi', 'rent', 'llm'],
                       help='指定获取的数据类型')
    parser.add_argument('--cities', type=str, default='',
                       help='租售比数据: 城市列表(逗号分隔)')
    parser.add_argument('--generate-code', action='store_true',
                       help='生成采集代码 (需要配合 --llm 使用)')
    
    args = parser.parse_args()
    
    if args.generate_code:
        # 生成采集代码模式
        from src.data_fetchers.llm_data_fetcher import generate_collector
        import json
        
        print("生成采集代码...")
        for metric in ['ACI', 'FPI', 'LPR']:
            code = generate_collector(metric)
            filename = f"fetcher_{metric.lower()}.py"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"✅ 已生成 {filename}")
        print("\n使用说明:")
        print("1. 编辑生成的 fetcher_*.py 文件，填写实际采集逻辑")
        print("2. 运行: python fetcher_*.py")
        
    elif args.llm or args.source == 'llm':
        run_llm_data()
    elif args.rent or args.source == 'rent':
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
