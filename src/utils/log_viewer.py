"""
后台日志查看器 — Background Log Viewer
在 Streamlit 侧边栏显示实时日志
"""
from __future__ import annotations

import os
import streamlit as st
from pathlib import Path
from datetime import datetime


def get_log_file_path() -> Path:
    """获取日志文件路径"""
    # 项目根目录
    root = Path(__file__).resolve().parent
    log_path = root / "logs" / "app.log"
    
    # 如果不存在，尝试上级目录
    if not log_path.exists():
        log_path = root.parent / "logs" / "app.log"
    
    return log_path


def get_log_lines(n: int = 100) -> list[str]:
    """读取最近的 n 行日志"""
    log_path = get_log_file_path()
    
    if not log_path.exists():
        return [f"日志文件不存在: {log_path}"]
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return lines[-n:] if len(lines) > n else lines
    except Exception as e:
        return [f"读取日志失败: {e}"]


def render_log_viewer():
    """渲染日志查看器组件"""
    st.sidebar.divider()
    st.sidebar.subheader("📋 后台日志")
    
    # 日志刷新控制
    col1, col2 = st.sidebar.columns([2, 1])
    with col1:
        n_lines = st.sidebar.slider("显示行数", 20, 500, 100, key="log_lines")
    with col2:
        if st.sidebar.button("🔄", key="refresh_log"):
            st.rerun()
    
    # 自动刷新选项
    auto_refresh = st.sidebar.checkbox("自动刷新", value=False, key="auto_refresh_logs")
    if auto_refresh:
        st.sidebar.markdown("*每 5 秒自动刷新*")
    
    # 读取日志
    lines = get_log_lines(n_lines)
    
    # 日志过滤
    log_filter = st.sidebar.selectbox(
        "日志级别",
        ["全部", "DEBUG", "INFO", "WARNING", "ERROR"],
        key="log_filter"
    )
    
    # 过滤日志
    filtered_lines = lines
    if log_filter != "全部":
        filtered_lines = [l for l in lines if f"| {log_filter} |" in l]
    
    # 显示日志
    st.sidebar.container(height=400, border=True)
    
    # 使用 expander 显示更多日志
    with st.sidebar.expander(f"📜 查看日志 ({len(filtered_lines)} 行)", expanded=False):
        log_text = "".join(filtered_lines)
        st.text(log_text)
    
    # 显示日志文件信息
    log_path = get_log_file_path()
    if log_path.exists():
        mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        st.sidebar.caption(f"最后更新: {mtime.strftime('%H:%M:%S')}")


def check_data_freshness() -> dict:
    """检查数据新鲜度"""
    from src.utils.db import get_engine
    import pandas as pd
    
    result = {
        "status": "unknown",
        "tables": {}
    }
    
    try:
        engine = get_engine()
        
        # 检查各表最新日期
        tables = ["macro_aci_data", "financial_fpi_data", "land_lpr_data", "model_ci_index"]
        
        for table in tables:
            try:
                df = pd.read_sql(f"SELECT MAX(date) as max_date FROM {table}", con=engine)
                if not df.empty and df.iloc[0]["max_date"]:
                    max_date = pd.to_datetime(df.iloc[0]["max_date"])
                    days_ago = (datetime.now() - max_date).days
                    result["tables"][table] = {
                        "max_date": max_date.strftime("%Y-%m-%d"),
                        "days_ago": days_ago
                    }
            except:
                result["tables"][table] = {"max_date": "N/A", "days_ago": -1}
        
        # 判断状态
        max_days = max([v["days_ago"] for v in result["tables"].values() if v["days_ago"] >= 0], default=0)
        
        if max_days <= 1:
            result["status"] = "fresh"
        elif max_days <= 7:
            result["status"] = "stale"
        else:
            result["status"] = "old"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def render_data_status():
    """渲染数据状态组件"""
    st.sidebar.divider()
    st.sidebar.subheader("📊 数据状态")
    
    # 刷新按钮
    if st.sidebar.button("🔄 刷新状态", key="refresh_status"):
        st.rerun()
    
    # 检查数据新鲜度
    freshness = check_data_freshness()
    
    # 显示状态
    status_emoji = {
        "fresh": "🟢",
        "stale": "🟡",
        "old": "🔴",
        "unknown": "⚪"
    }
    
    status_text = {
        "fresh": "数据最新",
        "stale": "数据较旧",
        "old": "需要更新",
        "unknown": "未知"
    }
    
    st.sidebar.write(f"{status_emoji.get(freshness['status'], '⚪')} **{status_text.get(freshness['status'], '未知')}**")
    
    # 显示各表数据日期
    with st.sidebar.expander("📅 各表数据日期"):
        if "tables" in freshness:
            for table, info in freshness["tables"].items():
                table_short = table.replace("macro_", "").replace("financial_", "").replace("land_", "").replace("model_", "")
                st.write(f"• {table_short}: {info['max_date']} ({info['days_ago']}天前)")
    
    # 重新运行数据管道按钮
    st.sidebar.divider()
    if st.sidebar.button("🚀 重新获取数据", key="rerun_pipeline"):
        with st.spinner("正在更新数据..."):
            import sys
            sys.path.insert(0, ".")
            from src.data_fetchers.run_all import run_pipeline
            run_pipeline()
        st.rerun()


# 在侧边栏调用
def init_sidebar_components():
    """初始化侧边栏组件"""
    render_log_viewer()
    render_data_status()
