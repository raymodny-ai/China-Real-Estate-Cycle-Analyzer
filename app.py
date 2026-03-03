"""
streamlit app.py - 中国房价底部预测模型 Dashboard

更新说明:
- 集成新的回测模块 v2.0
- 支持真正的量化回测指标展示
- 添加策略对比功能
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils.db import get_engine
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="中国房价底部预测模型 (CI Model)", layout="wide")

st.title("中国房价底部预测模型 (China Housing Market Bottom Predictor)")
st.markdown("基于「库存去化与银行信用约束模型」，通过量化多维市场指标，测算房价周期底部。")

# 连接数据库
engine = get_engine()

# Load Data
try:
    aci_df = pd.read_sql('macro_aci_data', con=engine)
    fpi_df = pd.read_sql('financial_fpi_data', con=engine)
    lpr_df = pd.read_sql('land_lpr_data', con=engine)
    ci_df = pd.read_sql('model_ci_index', con=engine)
    backtest_df = pd.read_sql('backtest_results', con=engine)
    japan_df = pd.read_sql('japan_comparison', con=engine)
    
    # 尝试读取回测指标
    try:
        metrics_df = pd.read_sql('backtest_metrics', con=engine)
        has_metrics = True
    except:
        has_metrics = False
        
except Exception as e:
    st.error(f"Error loading data: {e}. Please run data fetchers first.")
    st.stop()
    
# Clean data
ci_df['date'] = pd.to_datetime(ci_df['date'])
backtest_df['date'] = pd.to_datetime(backtest_df['date'])

# 创建标签页
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "判断口诀与现状", 
    "CI复合综合指标", 
    "核心三大指标(ACI/FPI/LPR)", 
    "历史回测",
    "中日对比"
])

with tab1:
    st.header("底部确认判断口诀")
    st.markdown("逻辑链条: `需求端萎缩 -> 库存堆高 -> 现金流紧张 -> 银行收缩 -> 土地流拍 -> 价格触底`")
    
    col1, col2, col3 = st.columns(3)
    
    # Evaluate latest conditions
    latest_ci = ci_df.iloc[-1]
    
 "满足" if latest_ci['I    cond1 =_ACI'] == 1 else "不满足"
    col1.metric("1. 库存 < 两年 (ACI条件)", cond1)
    
    cond2 = "满足" if latest_ci['I_FPI'] == 1 else "不满足"
    col2.metric("2. 融资转正 (FPI条件)", cond2)
    
    cond3 = "满足" if latest_ci['I_LPR'] == 1 else "不满足"
    col3.metric("3. 土地回暖 (LPR条件)", cond3)
    
    st.subheader("现状结论")
    if latest_ci['I_ACI'] == 1 and latest_ci['I_FPI'] == 1 and latest_ci['I_LPR'] == 1:
        st.success("✅ 确认：底部特征已完全显现。")
    else:
        st.warning("⚠️ 现状：仍远离底部确认。")

with tab2:
    st.header("CI复合研判指数 (Composite Index)")
    st.markdown("CI由三个子条件触发器构成。当三大核心指标同时指向积极信号时，CI指数上升，预示底部共振最强。")
    fig = px.line(ci_df, x='date', y='CI', title="CI复合指标动态走势")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("核心三大指标详情")
    
    st.subheader("1. 去化周期 ACI (月度)")
    fig_aci = px.line(aci_df, x='date', y='aci', title="可售库存面积与销售面积比 (ACI)")
    fig_aci.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="警戒水位 (2年/24个月)")
    st.plotly_chart(fig_aci, use_container_width=True)
    
    st.subheader("2. 房企资金链压力指数 FPI")
    fig_fpi = px.bar(fpi_df, x='date', y='net_financing_cash_flow', title="核心房企净融资额度")
    fig_fpi.add_hline(y=0, line_dash="dash", line_color="green", annotation_text="资金转正红线")
    st.plotly_chart(fig_fpi, use_container_width=True)
    
    st.subheader("3. 土地溢价拍买率 LPR")
    fig_lpr = px.line(lpr_df, x='date', y='premium_rate', title="土地溢价率走势 (%)")
    st.plotly_chart(fig_lpr, use_container_width=True)

with tab4:
    st.header("CI与房价指数关系回测")
    
    # 显示回测指标 (如果可用)
    if has_metrics and len(metrics_df) > 0:
        st.subheader("📊 回测指标")
        
        m = metrics_df.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总收益", f"{m.get('total_return', 0):.2%}")
        col2.metric("年化收益", f"{m.get('annual_return', 0):.2%}")
        col3.metric("Sharpe", f"{m.get('sharpe_ratio', 0):.2f}")
        col4.metric("最大回撤", f"{m.get('max_drawdown', 0):.2%}")
        
        col5, col6, col7 = st.columns(3)
        col5.metric("年化波动", f"{m.get('annual_volatility', 0):.2%}")
        col6.metric("胜率", f"{m.get('win_rate', 0):.2%}")
        col7.metric("平均仓位", f"{m.get('avg_position', 0):.2%}")
        
        st.divider()
    
    # 资金曲线对比
    st.subheader("📈 资金曲线对比")
    
    if 'cumulative_strategy' in backtest_df.columns and 'cumulative_asset' in backtest_df.columns:
        # 新版回测结果
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(
            x=backtest_df['date'], 
            y=backtest_df['cumulative_strategy'], 
            mode='lines', 
            name='CI策略'
        ))
        fig_bt.add_trace(go.Scatter(
            x=backtest_df['date'], 
            y=backtest_df['cumulative_asset'], 
            mode='lines', 
            name='买入持有',
            line=dict(dash='dot')
        ))
        fig_bt.update_layout(
            title="CI策略 vs 买入持有",
            xaxis_title="日期",
            yaxis_title="累计收益"
        )
    else:
        # 旧版模拟结果
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(
            x=backtest_df['date'], 
            y=backtest_df['HPI'], 
            mode='lines', 
            name='模拟房价指数'
        ))
        fig_bt.add_trace(go.Scatter(
            x=backtest_df['date'], 
            y=backtest_df['CI']*100, 
            mode='lines', 
            name='CI (×100)',
            line=dict(dash='dot')
        ))
        fig_bt.update_layout(
            title="CI触发与房价指数的负反馈推演",
            xaxis_title="日期",
            yaxis_title="指数"
        )
    
    st.plotly_chart(fig_bt, use_container_width=True)
    
    # 策略说明
    st.info("""
    **策略说明 (v2.0)**:
    - CI >= 0.7: 信号 -1 (减仓/做空)
    - CI <= 0.3: 信号 +1 (加仓/做多)
    - 中间区间: 信号 0 (观望)
    
    *注: 当前回测结果基于模拟资产价格，仅供参考演示。*
    """)

with tab5:
    st.header("与日本对比评估")
    st.dataframe(japan_df)
    st.markdown("""
    **中国特殊性分析**：
    1. 自定义中国弹性系数为 `1.05`。
    2. 房价预计面临下行调整空间。根据估算：房价预计下跌80% (日本参考)，目前仅下跌30%。
    3. 家庭负债率高企与老龄化深度叠加是关键影响因素。
    """)

# 页脚
st.divider()
st.caption("""
模型说明:
- ACI: 去化周期 (库存/销售)
- FPI: 资金链压力 (融资现金流)
- LPR: 土地溢价率
- CI: 复合指标

数据来源: 模拟数据/公开数据整合
""")
