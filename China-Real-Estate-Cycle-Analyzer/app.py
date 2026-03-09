"""
Streamlit Dashboard - Enhanced Version
With date picker, parameter sliders, and data export
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import os

# Import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import config
except ImportError:
    config = None

# Force cache clear
st.cache_data.clear()

# Page config
st.set_page_config(
    page_title="中国房地产周期分析器",
    page_icon="🏠",
    layout="wide"
)

# ==================== Sidebar Controls ====================
st.sidebar.title("⚙️ 控制面板")

# Date Range Selector
st.sidebar.subheader("📅 日期范围")
date_start = st.sidebar.date_input(
    "开始日期",
    value=pd.to_datetime("2020-01-01"),
    min_value=pd.to_datetime("2015-01-01"),
    max_value=pd.to_datetime("2026-12-31")
)
date_end = st.sidebar.date_input(
    "结束日期",
    value=pd.to_datetime("2026-12-31"),
    min_value=pd.to_datetime("2015-01-01"),
    max_value=pd.to_datetime("2026-12-31")
)

# City Selector
st.sidebar.subheader("🌆 城市选择")
city = st.sidebar.selectbox(
    "选择城市",
    ["全国", "北京", "上海", "深圳", "广州", "杭州", "南京", "成都", "武汉"],
    index=0
)

# Parameter Sliders
st.sidebar.subheader("📊 参数调整")

# Threshold sliders
aci_limit = st.sidebar.slider(
    "ACI 警戒线 (月)",
    min_value=6,
    max_value=36,
    value=24,
    step=1,
    help="去化周期警戒线，超过此值表示库存积压"
)

fpi_threshold = st.sidebar.slider(
    "FPI 阈值",
    min_value=-10000,
    max_value=10000,
    value=0,
    step=100,
    help="资金链压力阈值"
)

# Weight sliders
st.sidebar.subheader("⚖️ 复合指标权重")
w_aci = st.sidebar.slider("ACI 权重", 0.0, 1.0, 0.4, 0.05)
w_fpi = st.sidebar.slider("FPI 权重", 0.0, 1.0, 0.3, 0.05)
w_lpr = st.sidebar.slider("LPR 权重", 0.0, 1.0, 0.3, 0.05)

# Normalize weights
total_weight = w_aci + w_fpi + w_lpr
if total_weight > 0:
    w_aci, w_fpi, w_lpr = w_aci/total_weight, w_fpi/total_weight, w_lpr/total_weight

st.sidebar.markdown("---")
st.sidebar.markdown(f"**权重归一化**: ACI={w_aci:.0%}, FPI={w_fpi:.0%}, LPR={w_lpr:.0%}")

# ==================== Data Export ====================
st.sidebar.subheader("💾 数据导出")

@st.cache_data
def convert_df(df):
    """Convert DataFrame to CSV"""
    return df.to_csv(index=False).encode('utf-8')

# ==================== Data Generation ====================
@st.cache_data(ttl=0)
def generate_all_data():
    """Generate complete mock data"""
    
    dates = pd.date_range(start="2015-01-01", end="2026-12-01", freq='ME')
    n = len(dates)
    t = np.arange(n)
    
    # 1. ACI Data
    base_sales = 8000
    sales_trend = np.where(dates.year <= 2020, 100 * t, 100 * 20 - 200 * (dates.year - 2020))
    sales_seasonal = 1200 * np.sin(2 * np.pi * t / 12)
    sales_area = base_sales + sales_trend + sales_seasonal + np.random.normal(0, 400, n)
    sales_area = np.maximum(sales_area, 4000)
    
    inventory = np.zeros(n)
    inventory[0] = 30000
    for i in range(1, n):
        completion = 8000 + 30 * min(t[i], 80) + np.random.normal(0, 300)
        inventory[i] = inventory[i-1] + completion - sales_area[i]
        inventory[i] = max(inventory[i], 20000)
    
    aci_original = inventory / (sales_area + 1)
    
    # 2. FPI Data (Annual to Monthly)
    annual_fpi = {
        2015: 5000, 2016: 8000, 2017: 6000, 2018: 4000, 
        2019: 3000, 2020: -2000, 2021: -5000, 2022: -8000,
        2023: -6000, 2024: -4000, 2025: -3000, 2026: -2000
    }
    fpi_list = []
    for d in dates:
        year = d.year
        fpi_list.append(annual_fpi.get(year, 0))
    fpi_monthly = fpi_list + np.random.normal(0, 500, n)
    
    # 3. LPR Data
    lpr_base = 4.65
    lpr_changes = [0, 0, 0, -0.10, 0, 0, -0.05, -0.10, 0.10, 0]
    lpr_5y = np.array([lpr_base + sum(lpr_changes[:i+1]) + np.random.normal(0, 0.02) for i in range(n)])
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'sales_area': sales_area,
        'inventory': inventory,
        'aci': aci_original,
        'fpi': fpi_monthly,
        'lpr_5y': lpr_5y
    })
    
    return df

# ==================== Main Content ====================
st.title("🏠 中国房地产周期分析器")
st.markdown(f"**当前城市**: {city} | **日期**: {date_start.strftime('%Y-%m')} ~ {date_end.strftime('%Y-%m')}")

# Generate data
df = generate_all_data()

# Filter by date range
mask = (df['date'] >= pd.to_datetime(date_start)) & (df['date'] <= pd.to_datetime(date_end))
df_filtered = df[mask].copy()

# Calculate composite index
df_filtered['I_ACI'] = (df_filtered['aci'] < aci_limit).astype(int)
df_filtered['I_FPI'] = (df_filtered['fpi'] > fpi_threshold).astype(int)
df_filtered['I_LPR'] = np.gradient(df_filtered['lpr_5y']) > 0

# Composite Index
df_filtered['CI'] = (
    w_aci * (1 - df_filtered['aci'] / aci_limit) +
    w_fpi * (df_filtered['fpi'] - fpi_threshold) / 10000 +
    w_lpr * df_filtered['I_LPR'].astype(int)
)

# ==================== Dashboard ====================
# Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    latest_aci = df_filtered['aci'].iloc[-1]
    aci_status = "🟢 正常" if latest_aci < aci_limit else "🔴 警戒"
    st.metric("ACI (去化周期)", f"{latest_aci:.1f} 月", delta=aci_status)

with col2:
    latest_fpi = df_filtered['fpi'].iloc[-1]
    fpi_status = "🟢 充足" if latest_fpi > 0 else "🔴 紧张"
    st.metric("FPI (资金链)", f"{latest_fpi:,.0f}", delta=fpi_status)

with col3:
    latest_lpr = df_filtered['lpr_5y'].iloc[-1]
    lpr_change = latest_lpr - df_filtered['lpr_5y'].iloc[-12] if len(df_filtered) > 12 else 0
    st.metric("5Y LPR", f"{latest_lpr:.2f}%", delta=f"{lpr_change:+.2f}%")

with col4:
    latest_ci = df_filtered['CI'].iloc[-1]
    ci_status = "🟢 周期回升" if latest_ci > 0.3 else "🔴 周期下行"
    st.metric("复合指数 (CI)", f"{latest_ci:.2f}", delta=ci_status)

# Charts
st.subheader("📈 周期指标走势")

tab1, tab2, tab3, tab4 = st.tabs(["ACI", "FPI", "LPR", "复合指数"])

with tab1:
    fig_aci = go.Figure()
    fig_aci.add_trace(go.Scatter(
        x=df_filtered['date'], y=df_filtered['aci'],
        mode='lines', name='ACI',
        line=dict(color='#FF6B6B', width=2)
    ))
    fig_aci.add_hline(y=aci_limit, line_dash="dash", line_color="red", 
                       annotation_text=f"警戒线 ({aci_limit}月)")
    fig_aci.update_layout(
        title=f"去化周期 (ACI) - {city}",
        xaxis_title="日期",
        yaxis_title="月",
        hovermode="x unified"
    )
    st.plotly_chart(fig_aci, use_container_width=True)

with tab2:
    fig_fpi = go.Figure()
    fig_fpi.add_trace(go.Scatter(
        x=df_filtered['date'], y=df_filtered['fpi'],
        mode='lines', name='FPI',
        line=dict(color='#4ECDC4', width=2),
        fill='tozeroy'
    ))
    fig_fpi.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_fpi.update_layout(
        title=f"资金链 (FPI) - {city}",
        xaxis_title="日期",
        yaxis_title="亿元",
        hovermode="x unified"
    )
    st.plotly_chart(fig_fpi, use_container_width=True)

with tab3:
    fig_lpr = go.Figure()
    fig_lpr.add_trace(go.Scatter(
        x=df_filtered['date'], y=df_filtered['lpr_5y'],
        mode='lines', name='5Y LPR',
        line=dict(color='#45B7D1', width=2)
    ))
    fig_lpr.update_layout(
        title=f"5年期LPR - {city}",
        xaxis_title="日期",
        yaxis_title="%",
        hovermode="x unified"
    )
    st.plotly_chart(fig_lpr, use_container_width=True)

with tab4:
    fig_ci = go.Figure()
    colors = ['#10B981' if v > 0.3 else '#EF4444' for v in df_filtered['CI']]
    fig_ci.add_trace(go.Scatter(
        x=df_filtered['date'], y=df_filtered['CI'],
        mode='lines+markers',
        name='CI',
        marker=dict(color=colors, size=4),
        line=dict(color='#8B5CF6', width=2)
    ))
    fig_ci.add_hline(y=0.3, line_dash="dash", line_color="green", annotation_text="回升线")
    fig_ci.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_ci.update_layout(
        title=f"复合周期指数 (CI) - {city}",
        xaxis_title="日期",
        yaxis_title="指数",
        hovermode="x unified"
    )
    st.plotly_chart(fig_ci, use_container_width=True)

# ==================== Data Table ====================
st.subheader("📋 详细数据")

# Show data with export
st.dataframe(
    df_filtered[['date', 'aci', 'fpi', 'lpr_5y', 'CI']].sort_values('date', ascending=False),
    use_container_width=True
)

# Export button
csv = convert_df(df_filtered)
st.download_button(
    label="📥 导出 CSV",
    data=csv,
    file_name=f"china_real_estate_{city}_{date_start.strftime('%Y%m')}_{date_end.strftime('%Y%m')}.csv",
    mime="text/csv"
)

# ==================== Footer ====================
st.markdown("---")
st.caption(f"数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ACI阈值: {aci_limit}月 | 权重: ACI={w_aci:.0%}, FPI={w_fpi:.0%}, LPR={w_lpr:.0%}")

# ==================== AI 分析功能 ====================
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 分析")

# API Key 配置
api_key = st.sidebar.text_input(
    "DeepSeek API Key", 
    type="password",
    help="输入 DeepSeek API Key (可选，使用模拟模式不需要)"
)

# 使用模拟/真实模式
# ==================== AI 分析功能 ====================
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 分析")

# API Key 配置
api_key = st.sidebar.text_input("DeepSeek API Key", type="password", help="输入 API Key")
use_mock = st.sidebar.checkbox("使用模拟 AI", value=True)

# 点击生成分析
if st.sidebar.button("生成分析报告", key="gen_report"):
    st.session_state.show_pdf = True
    with st.spinner("AI 分析中..."):
        try:
            from src.ai import analyze_market
            from src.reports import generate_report
            
            indicators = {
                'aci': df_filtered['aci'].iloc[-1],
                'fpi': df_filtered['fpi'].iloc[-1],
                'lpr_5y': df_filtered['lpr_5y'].iloc[-1],
                'CI': df_filtered['CI'].iloc[-1]
            }
            
            st.session_state.analysis = analyze_market(city, indicators, api_key, use_mock)
            st.session_state.pdf_data = generate_report(city, indicators, st.session_state.analysis)
            st.session_state.indicators = indicators
        except Exception as e:
            st.error(f"分析失败: {e}")

# 显示结果
if st.session_state.get('analysis'):
    st.subheader("🤖 AI 分析报告")
    st.markdown(st.session_state.analysis)
    
    st.subheader("📥 下载 PDF 报告")
    st.download_button(
        label="📥 下载 PDF 报告",
        data=st.session_state.pdf_data,
        file_name=f"report_{city}.pdf",
        mime="application/pdf"
    )
    
    # Telegram
    if st.button("发送到 Telegram"):
        from src.notifications import send_alert
        send_alert(city, st.session_state.indicators, st.session_state.analysis)
