"""
健康检查工具 — Health Check
检查数据新鲜度与对外 API 的连通性。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import pandas as pd
import requests

from src.utils.db import get_engine
from src.utils.logger import get_logger

logger = get_logger("health")

def check_db_freshness() -> dict[str, dict[str, str]]:
    """检查各个表里的数据新鲜度"""
    engine = get_engine()
    tables = {
        "macro_aci_data": "去化周期 ACI",
        "financial_fpi_data": "资金压力 FPI",
        "land_lpr_data": "土地溢价 LPR",
        "model_ci_index": "CI 复合指数"
    }
    
    status = {}
    now = datetime.now()
    
    for table, name in tables.items():
        try:
            df = pd.read_sql(f"SELECT MAX(date) as last_date FROM {table}", con=engine)
            if df.empty or pd.isna(df.iloc[0]["last_date"]):
                status[name] = {"status": "error", "message": "表为空或不存在"}
                continue
                
            last_dt = pd.to_datetime(df.iloc[0]["last_date"])
            days_diff = (now - last_dt).days
            
            if days_diff > 90:
                s = "warning"
                msg = f"数据陈旧 (最后更新于 {last_dt.strftime('%Y-%m-%d')}，距今 {days_diff} 天)"
            else:
                s = "ok"
                msg = f"数据正常 (最后更新于 {last_dt.strftime('%Y-%m-%d')})"
                
            status[name] = {"status": s, "message": msg}
        except Exception as e:
            status[name] = {"status": "error", "message": f"查询失败: {e}"}
            
    return status

def check_api_connectivity() -> dict[str, dict[str, str]]:
    """检查主要外部数据源的连通性"""
    endpoints = {
        "EastMoney (东方财富 API)": "https://datacenter.eastmoney.com",
        "NBS (国家统计局 API代理 - Sina)": "https://finance.sina.com.cn"
    }
    
    status = {}
    for name, url in endpoints.items():
        try:
            # 简单的 GET 请求检测连通性
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                status[name] = {"status": "ok", "message": "连接正常"}
            else:
                status[name] = {"status": "warning", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            status[name] = {"status": "error", "message": f"无法连接: {e}"}
            
    return status

def run_health_checks():
    """执行并打印所有健康检查"""
    logger.info("开始执行系统健康检查...")
    
    db_res = check_db_freshness()
    logger.info("=== 数据库数据新鲜度 ===")
    has_error = False
    for name, info in db_res.items():
        log_msg = f"{name}: [{info['status'].upper()}] {info['message']}"
        if info["status"] == "error":
            logger.error(log_msg)
            has_error = True
        elif info["status"] == "warning":
            logger.warning(log_msg)
            has_error = True
        else:
            logger.info(log_msg)
            
    api_res = check_api_connectivity()
    logger.info("=== 外部 API 连通性 ===")
    for name, info in api_res.items():
        log_msg = f"{name}: [{info['status'].upper()}] {info['message']}"
        if info["status"] == "error":
            logger.error(log_msg)
            has_error = True
        elif info["status"] == "warning":
            logger.warning(log_msg)
            has_error = True
        else:
            logger.info(log_msg)
            
    if has_error:
        logger.warning("系统存在部分警告/错误，建议检查。")
    else:
        logger.info("系统健康检查通过，状态完美！")

if __name__ == "__main__":
    run_health_checks()
