"""
完整数据 + 模型管道 — Run All Pipeline
一键运行全部数据获取、指标计算和回测。
"""
from __future__ import annotations

import sys
import os

# ── 确保项目根目录在 Python 路径中 ────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.utils.logger import get_logger, setup_global_exceptions
from src.data_fetchers.macro_data import save_aci_to_db
from src.data_fetchers.financial_data import save_fpi_to_db
from src.data_fetchers.land_data import save_lpr_to_db
from src.services.cycle_analyzer import CycleAnalyzerService
from src.services.backtest import BacktestService
logger = get_logger("pipeline")


import argparse

def run_pipeline(force_update: bool = False) -> None:
    """按顺序执行完整的数据→模型管道。"""
    logger.info("=" * 60)
    logger.info("启动完整数据管道 (China RE Cycle Analyzer)")
    logger.info("=" * 60)

    # Step 1: 数据获取
    logger.info(f"[1/5] 获取 ACI 去化周期数据... (强制更新={force_update})")
    save_aci_to_db(force_update=force_update)

    logger.info(f"[2/5] 获取 FPI 资金链数据... (强制更新={force_update})")
    save_fpi_to_db(force_update=force_update)

    logger.info(f"[3/5] 获取 LPR 土地溢价率数据... (强制更新={force_update})")
    save_lpr_to_db(force_update=force_update)

    # Step 2: 模型计算
    logger.info("[4/5] 计算 CI 复合研判指数...")
    analyzer = CycleAnalyzerService()
    result = analyzer.calculate_ci_index()
    if result is None:
        logger.error("CI 计算失败，中止管道。")
        sys.exit(1)

    # Step 3: 回测 + 中日对比
    logger.info("[5/5] 运行回测 + 生成中日对比数据...")
    bt_service = BacktestService()
    bt_service.run_backtest()
    bt_service.get_japanese_comparison()

    logger.info("=" * 60)
    logger.info("✅ 全部管道步骤完成！运行 `streamlit run app.py` 查看仪表盘。")
    logger.info("=" * 60)


if __name__ == "__main__":
    setup_global_exceptions()
    parser = argparse.ArgumentParser(description="运行完整数据管道")
    parser.add_argument("--real", action="store_true", help="强制使用真实 API 更新数据，忽略缓存")
    args = parser.parse_args()
    
    run_pipeline(force_update=args.real)
