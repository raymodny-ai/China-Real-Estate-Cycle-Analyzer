"""
Streamlit 可视化面板 (优化版)
包含【未来底价估算】面板
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# 设置页面
st.set_page_config(
    page_title="中国房地产周期分析器 (优化版)",
    page_icon="🏠",
    layout="wide"
)

# 标题
st.title("🏠 中国房地产周期底部预测系统")
st.markdown("**优化版本：广义库存 | 动态阈值 | 弹性系数预测 | 政策阻尼**")

# 侧边栏 - 参数设置
st.sidebar.header("⚙️ 参数设置")

# 弹性系数设置
elasticity = st.sidebar.slider(
    "弹性系数 (中国: 1.05)", 
    min_value=0.8, 
    max_value=1.5, 
    value=1.05, 
    step=0.01
)

# 目标跌幅
target_decline = st.sidebar.slider(
    "目标跌幅 (%)", 
    min_value=50, 
    max_value=90, 
    value=80, 
    step=5
) / 100

# 当前跌幅
current_decline = st.sidebar.slider(
    "当前跌幅 (%)", 
    min_value=10, 
    max_value=50, 
    value=30, 
    step=5
) / 100

# 政策阻尼
policy_damping = st.sidebar.slider(
    "政策干预阻尼系数", 
    min_value=0.8, 
    max_value=2.0, 
    value=1.2, 
    step=0.1
)

# 主界面标签页
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 底部判断", 
    "📊 CI复合指标", 
    "📉 核心三大指标",
    "🔮 未来底价估算",  # 新增
    "📈 历史回测",
    "🇨🇳中日对比"
])

with tab1:
    st.header("底部信号判断")
    
    # 模拟数据展示
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("ACI (去化周期)", "28.5 个月", "🔴")
    with col2:
        st.metric("FPI (资金链)", "-2,300 亿元", "🔴")
    with col3:
        st.metric("LPR (土地溢价率)", "8.2%", "🟢")
    
    st.divider()
    
    # 动态阈值 vs 绝对阈值
    st.subheader("ACI 判断方式对比")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📌 绝对阈值 (传统)")
        st.write("- ACI < 24个月 → 买入信号")
        st.write("- 简单但不够精确")
        
    with col2:
        st.success("✨ 动态阈值 (优化版)")
        st.write("- ACI < 5年滚动均值 AND ACI < 24个月")
        st.write("- 更符合市场实际周期")
    
    # 底部条件
    st.divider()
    st.subheader("🔔 底部确认条件")
    
    conditions = [
        ("ACI (广义库存去化)", "❌ 未满足"),
        ("FPI (资金链压力)", "❌ 未满足"),
        ("LPR (土地价格止跌)", "❌ 未满足"),
    ]
    
    for name, status in conditions:
        st.write(f"- **{name}**: {status}")
    
    st.warning("⚠️ 当前状态：距离底部仍有较大距离")

with tab2:
    st.header("CI 复合指标走势")
    st.info("📊 CI = ACI×0.4 + FPI×0.3 + LPR×0.3")
    
    # 模拟图表
    dates = pd.date_range(start="2020-01-01", end="2024-12-01", freq='ME')
    ci_values = np.random.uniform(0.2, 0.8, len(dates))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, 
        y=ci_values,
        mode='lines',
        name='CI',
        line=dict(color='#636EFA', width=2)
    ))
    
    # 阈值线
    fig.add_hline(y=0.7, line_dash="dash", line_color="green", annotation_text="买入线(0.7)")
    fig.add_hline(y=0.3, line_dash="dash", line_color="red", annotation_text="卖出线(0.3)")
    
    fig.update_layout(
        title="CI 复合指标走势",
        xaxis_title="时间",
        yaxis_title="CI 值",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("核心三大指标详情")
    
    # ACI 对比
    st.subheader("1. ACI (去化周期)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("原始 ACI (新房)", "26 个月")
    with col2:
        st.metric("广义 ACI (含二手+法拍)", "42 个月", "+16")
    
    st.caption("💡 广义 ACI 更准确反映真实库存压力")
    
    # LPR 双轨制
    st.divider()
    st.subheader("2. LPR (土地溢价率) - 双轨制验证")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("溢价率", "8.2%")
    with col2:
        st.metric("溢价率斜率", "0.15", "↗️ 回升中")
    with col3:
        st.metric("均价斜率", "-5.2", "↘️ 仍在下跌")
    
    st.error("❌ 双轨制验证：仅溢价率回升，均价仍在下跌，不满足条件")
    
    # FPI
    st.divider()
    st.subheader("3. FPI (资金链压力)")
    st.metric("房企净融资现金流", "-3,200 亿元", "-15%")

with tab6:
    st.header("🇨🇳中日对比")
    st.info("📚 参考日本泡沫经济经验")
    
    # 日本数据
    japan_data = {
        'phase': ['泡沫期', '破裂期', '调整期', '恢复期'],
        'years': [1986-1991, 1991-1995, 1995-2005, 2005-至今],
        'japan_decline': [0, -50, -70, -65],
        'china_current': [-30]
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**日本经验**")
        st.write("- 泡沫破裂后跌幅: ~70%")
        - 调整时长: ~15年
        - 关键因素: 老龄化、杠杆率
        
    with col2:
        st.write("**中国现状**")
        st.write(f"- 当前跌幅: ~{current_decline*100:.0f}%")
        st.write(f"- 目标跌幅: ~{target_decline*100:.0f}%")
        st.write(f"- 剩余空间: ~{(target_decline-current_decline)*100:.0f}%")

# ==================== 未来底价估算 (新增核心功能) ====================
with tab4:
    st.header("🔮 未来底价估算")
    st.markdown("**基于弹性系数法 + 宏观惩罚因子 + 政策阻尼**")
    
    # 核心参数展示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("弹性系数", f"{elasticity}")
    with col2:
        st.metric("当前跌幅", f"{current_decline*100:.0f}%")
    with col3:
        st.metric("目标跌幅", f"{target_decline*100:.0f}%")
    with col4:
        st.metric("剩余空间", f"{(target_decline-current_decline)*100:.0f}%")
    
    st.divider()
    
    # 预测引擎
    from src.models.predict_engine import PricePredictionEngine
    
    engine = PricePredictionEngine()
    engine.CHINA_ELASTICITY_COEFFICIENT = elasticity
    engine.current_decline_rate = current_decline
    
    # 获取宏观惩罚因子
    macro = engine.get_macro_penalty_factors()
    
    # 显示惩罚因子
    st.subheader("📊 宏观惩罚因子")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("老龄化率", f"{macro['aging_rate']*100:.1f}%", f"惩罚 {macro['aging_penalty']:.2f}x")
    with col2:
        st.metric("居民杠杆率", f"{macro['leverage_rate']*100:.0f}%", f"惩罚 {macro['leverage_penalty']:.2f}x")
    with col3:
        st.metric("综合惩罚", f"{macro['combined_penalty']:.2f}x")
    
    # 预测曲线
    st.divider()
    st.subheader("📈 价格走势预测")
    
    # 生成预测数据
    curve = engine.predict_price_curve(
        months_ahead=36,
        current_price=100,
        monthly_decline_rate=target_decline/36,
        include_penalty=True
    )
    
    # 绘制图表
    fig = go.Figure()
    
    # 价格曲线
    fig.add_trace(go.Scatter(
        x=curve['date'],
        y=curve['price_pct'],
        mode='lines+markers',
        name='预测价格',
        line=dict(color='#00CC96', width=3)
    ))
    
    # 当前位置标记
    fig.add_vline(x=curve['date'].iloc[0], line_dash="dash", line_color="yellow")
    
    # 目标线
    fig.add_hline(y=(1-target_decline)*100, line_dash="dot", line_color="red", 
                  annotation_text=f"目标底价 {(1-target_decline)*100:.0f}%")
    
    # 当前线
    fig.add_hline(y=(1-current_decline)*100, line_dash="dot", line_color="yellow",
                  annotation_text=f"当前位置 {(1-current_decline)*100:.0f}%")
    
    # 填充区域
    fig.add_hline(y=50, line_color="gray", line_width=1)
    
    fig.update_layout(
        title="房价预测曲线 (基准价=100)",
        xaxis_title="时间",
        yaxis_title="价格 (%)",
        height=500,
        yaxis_range=[0, 110]
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 底部时间预测
    st.divider()
    st.subheader("⏰ 底部时间预测")
    
    # 政策阻尼调整
    adjusted_damping = policy_damping * macro['combined_penalty']
    
    bottom = engine.calculate_bottom_time(
        current_decline=current_decline,
        target_decline=target_decline,
        monthly_decline_rate=target_decline/36,
        policy_damping=adjusted_damping
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("基础月数", f"{bottom['base_months_to_bottom']:.0f} 月")
    with col2:
        st.metric("政策阻尼", f"{bottom['policy_damping']:.2f}x")
    with col3:
        st.metric("调整后月数", f"{bottom['adjusted_months_to_bottom']:.0f} 月")
    with col4:
        st.metric("预计底部", bottom['bottom_date'])
    
    # 状态显示
    if bottom['confidence'] == '高':
        st.success(f"✅ 置信度: {bottom['confidence']} - 市场接近底部")
    elif bottom['confidence'] == '中':
        st.warning(f"⚠️ 置信度: {bottom['confidence']} - 仍有政策干扰")
    else:
        st.error(f"❌ 置信度: {bottom['confidence']} - 远离底部确认")
    
    # 结论
    st.divider()
    st.subheader("📋 预测结论")
    
    conclusion = f"""
    | 指标 | 数值 |
    |------|------|
    | 弹性系数 | {elasticity} |
    | 当前跌幅 | {current_decline*100:.0f}% |
    | 目标跌幅 | {target_decline*100:.0f}% |
    | 剩余跌幅 | {(target_decline-current_decline)*100:.0f}% |
    | 宏观惩罚 | {macro['combined_penalty']:.2f}x |
    | 政策阻尼 | {policy_damping:.1f}x |
    | 预计底部时间 | {bottom['bottom_date']} |
    | 底部置信度 | {bottom['confidence']} |
    """
    
    st.markdown(conclusion)
    
    st.info(f"""
    💡 **关键发现**:
    - 当前房价相当于周期高点的 {(1-current_decline)*100:.0f}%
    - 距离目标底价还有 {(target_decline-current_decline)*100:.0f}% 下跌空间
    - 考虑宏观因素后，底部确认可能延后至 {bottom['bottom_date']}
    """)

with tab5:
    st.header("📈 历史回测")
    st.info("Coming Soon...")

# 底部信息
st.divider()
st.caption("🏠 中国房地产周期分析器 | 优化版本 | 数据仅供参考，不构成投资建议")
