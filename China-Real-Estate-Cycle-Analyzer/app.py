"""
Streamlit 可视化面板 (详细推理版)
显示所有计算和推理过程
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置页面
st.set_page_config(
    page_title="中国房地产周期分析器",
    page_icon="🏠",
    layout="wide"
)

# ==================== 数据生成模块 ====================
@st.cache_data
def generate_all_data():
    """生成完整的模拟数据"""
    
    dates = pd.date_range(start="2015-01-01", end="2024-12-01", freq='ME')
    n = len(dates)
    t = np.arange(n)
    
    # 1. ACI 数据
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
    
    # 2. 广义 ACI
    secondhand = 80 + t * 2 + np.random.normal(0, 5, n)
    secondhand_area = secondhand * 100 / 10000
    auction = 10 + np.maximum(0, t - 40) * 1.5 + np.random.normal(0, 3, n)
    auction_area = auction * 100 / 10000
    extended_inventory = inventory + secondhand_area + auction_area
    aci_extended = extended_inventory / (sales_area + 1)
    
    # 3. FPI
    net_financing = np.zeros(n)
    for i, date in enumerate(dates):
        year = date.year
        if year <= 2016:
            net_financing[i] = 8000 + np.random.normal(0, 500)
        elif year <= 2020:
            net_financing[i] = 5000 + np.random.normal(0, 800)
        elif year <= 2023:
            net_financing[i] = -3000 + 800 * (year - 2020) + np.random.normal(0, 500)
        else:
            net_financing[i] = -2000 + np.random.normal(0, 300)
    
    # 4. 土地数据
    premium_rate = np.zeros(n)
    land_price = np.zeros(n)
    for i, date in enumerate(dates):
        year, month = date.year, date.month
        if year <= 2016:
            base_p = 40 - (year - 2012) * 2
        elif year <= 2021:
            base_p = 30 - (year - 2017) * 3
        else:
            base_p = 12 - (year - 2022) * 2
        premium_rate[i] = max(base_p + 8 * np.sin(2 * np.pi * month / 12) + np.random.normal(0, 2), 0)
        
        if year <= 2021:
            base_lp = 3000 + year * 180
        else:
            base_lp = 6600 + (year - 2022) * 80
        land_price[i] = max(base_lp + 200 * np.sin(2 * np.pi * month / 12) + np.random.normal(0, 100), 2000)
    
    # 5. 房价
    price = 100 * np.ones(n)
    for i in range(1, n):
        if dates[i].year >= 2021:
            decline = 0.005 + np.random.normal(0.002, 0.001) * (dates[i].year - 2020)
            price[i] = price[i-1] * (1 - decline)
    
    decline_rate = 1 - price / 100
    
    return pd.DataFrame({
        'date': dates, 'sales_area': sales_area, 'inventory_area': inventory,
        'aci_original': aci_original, 'secondhand_area': secondhand_area,
        'auction_area': auction_area, 'extended_inventory': extended_inventory,
        'aci_extended': aci_extended, 'net_financing': net_financing,
        'premium_rate': premium_rate, 'land_price': land_price,
        'price': price, 'decline_rate': decline_rate,
    })

df = generate_all_data()

# ==================== 计算模块 ====================
def calculate_all_indicators(df):
    result = df.copy()
    steps = []
    
    # 1. ACI
    step1 = "### 1. ACI 指标计算\n\n"
    result['aci_ma12'] = result['aci_original'].rolling(12, min_periods=1).mean()
    result['aci_extended_ma12'] = result['aci_extended'].rolling(12, min_periods=1).mean()
    result['aci_5yr_ma'] = result['aci_extended'].rolling(60, min_periods=12).mean()
    result['I_ACI_absolute'] = (result['aci_original'] < 24).astype(int)
    result['I_ACI_dynamic'] = ((result['aci_extended'] < result['aci_5yr_ma']) & (result['aci_extended'] < 24)).astype(int)
    step1 += f"- 原始 ACI = {result['aci_original'].iloc[-1]:.1f} 个月\n- 广义 ACI = {result['aci_extended'].iloc[-1]:.1f} 个月\n- 5年均值 = {result['aci_5yr_ma'].iloc[-1]:.1f} 个月\n- 动态信号 = {result['I_ACI_dynamic'].iloc[-1]}\n"
    steps.append(step1)
    
    # 2. FPI
    step2 = "### 2. FPI 指标计算\n\n"
    result['I_FPI'] = (result['net_financing'] > 0).astype(int)
    step2 += f"- 净融资 = {result['net_financing'].iloc[-1]:,.0f} 亿元\n- FPI信号 = {result['I_FPI'].iloc[-1]}\n"
    steps.append(step2)
    
    # 3. LPR
    step3 = "### 3. LPR 双轨制计算\n\n"
    result['premium_ma6'] = result['premium_rate'].rolling(6, min_periods=3).mean()
    result['premium_slope'] = result['premium_rate'].rolling(6, min_periods=3).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)
    result['land_price_slope'] = result['land_price'].rolling(6, min_periods=3).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)
    cond1 = (result['premium_slope'] > 0) | (result['premium_rate'] > result['premium_ma6'])
    cond2 = result['land_price_slope'] > 0
    result['I_LPR'] = (cond1 & cond2).astype(int)
    step3 += f"- 溢价率 = {result['premium_rate'].iloc[-1]:.1f}%\n- 均价 = {result['land_price'].iloc[-1]:,.0f}元/㎡\n- LPR信号 = {result['I_LPR'].iloc[-1]}\n"
    steps.append(step3)
    
    # 4. CI
    step4 = "### 4. CI 复合指标\n\n"
    result['CI'] = result['I_ACI_dynamic'] * 0.4 + result['I_FPI'] * 0.3 + result['I_LPR'] * 0.3
    step4 += f"- CI = {result['CI'].iloc[-1]:.2f}\n"
    steps.append(step4)
    
    return result, steps

df_result, calculation_steps = calculate_all_indicators(df)

# ==================== UI ====================
st.title("🏠 中国房地产周期底部预测系统")
st.markdown("**详细推理版：展示所有计算过程和中间结果**")

# 侧边栏
st.sidebar.header("⚙️ 参数设置")
elasticity = st.sidebar.slider("弹性系数", 0.8, 1.5, 1.05, 0.01)
target_decline = st.sidebar.slider("目标跌幅 (%)", 50, 90, 80, 5) / 100
current_decline = st.sidebar.slider("当前跌幅 (%)", 10, 50, 30, 5) / 100
policy_damping = st.sidebar.slider("政策阻尼系数", 0.8, 2.0, 1.2, 0.1)

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🔍 推理过程", "🏠 底部判断", "📊 CI复合指标", 
    "📉 核心指标", "🔮 未来预测", "📈 历史回测", "📋 数据表"
])

latest = df_result.iloc[-1]

# Tab 1: 推理过程
with tab1:
    st.header("🧠 完整推理过程")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("日期", latest['date'].strftime('%Y-%m'))
    with col2: st.metric("销售面积", f"{latest['sales_area']:,.0f} 万㎡")
    with col3: st.metric("房价", f"{latest['price']*100:.1f}%")
    
    st.divider()
    
    for i, step in enumerate(calculation_steps):
        with st.expander(f"📐 步骤 {i+1}", expanded=True):
            st.markdown(step)
    
    # ACI 详情
    with st.expander("📊 ACI 推理详情", expanded=True):
        st.markdown(f"""
        **原始 ACI =** {latest['inventory_area']:,.0f} / {latest['sales_area']:,.0f} = **{latest['aci_original']:.1f} 个月**
        
        **广义 ACI =** ({latest['inventory_area']:,.0f} + {latest['secondhand_area']:.0f} + {latest['auction_area']:.0f}) / {latest['sales_area']:,.0f} = **{latest['aci_extended']:.1f} 个月**
        
        **动态判断:** ACI({latest['aci_extended']:.1f}) < 5年均值({latest['aci_5yr_ma']:.1f}) 且 < 24
        """)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['aci_original'], name='原始 ACI', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['aci_extended'], name='广义 ACI', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['aci_5yr_ma'], name='5年均值', line=dict(color='green', dash='dash')))
        fig.add_hline(y=24, line_dash="dot", line_color="orange", annotation_text="阈值24")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # FPI 详情
    with st.expander("💰 FPI 推理详情", expanded=True):
        st.markdown(f"**净融资 =** {latest['net_financing']:,.0f} 亿元 → {'安全' if latest['I_FPI'] else '危险'}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['net_financing'], fill='tozeroy', line=dict(color='red' if latest['net_financing'] < 0 else 'green')))
        fig.add_hline(y=0, line_color="gray")
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    # LPR 详情
    with st.expander("🏗️ LPR 双轨制推理", expanded=True):
        cond1 = latest['premium_slope'] > 0 or latest['premium_rate'] > latest['premium_ma6']
        cond2 = latest['land_price_slope'] > 0
        st.markdown(f"| 轨道 | 指标 | 结果 |")
        st.markdown(f"|------|------|------|")
        st.markdown(f"| 1 | 溢价率 {latest['premium_rate']:.1f}% | {'✓' if cond1 else '✗'} |")
        st.markdown(f"| 2 | 均价 {latest['land_price']:,.0f}元/㎡ | {'✓' if cond2 else '✗'} |")
        st.markdown(f"**LPR信号: {latest['I_LPR']} (1=双轨满足)**")
    
    # CI 详情
    with st.expander("📊 CI 复合指标推理", expanded=True):
        st.markdown(f"""
        **CI = ACI×0.4 + FPI×0.3 + LPR×0.3**
        
        = {latest['I_ACI_dynamic']}×0.4 + {latest['I_FPI']}×0.3 + {latest['I_LPR']}×0.3
        
        = {latest['I_ACI_dynamic']*0.4:.2f} + {latest['I_FPI']*0.3:.2f} + {latest['I_LPR']*0.3:.2f}
        
        = **{latest['CI']:.2f}**
        
        信号: {'强烈买入' if latest['CI']>=0.7 else '买入' if latest['CI']>=0.5 else '观望' if latest['CI']>=0.3 else '卖出'}
        """)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['CI'], fill='tozeroy', line=dict(color='purple')))
        fig.add_hline(y=0.7, line_dash="dash", line_color="green")
        fig.add_hline(y=0.3, line_dash="dash", line_color="red")
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)

# Tab 2: 底部判断
with tab2:
    st.header("🏠 底部信号判断")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("ACI", f"{latest['aci_extended']:.1f}月", delta=f"{latest['aci_5yr_ma']-latest['aci_extended']:.1f}")
    with col2: st.metric("FPI", f"{latest['net_financing']:,.0f}亿", delta="安全" if latest['I_FPI'] else "危险")
    with col3: st.metric("LPR", f"{latest['premium_rate']:.1f}%", delta="双轨" if latest['I_LPR'] else "未满足")
    
    st.divider()
    st.subheader("🔔 底部条件")
    conditions = [("ACI", latest['I_ACI_dynamic']), ("FPI", latest['I_FPI']), ("LPR", latest['I_LPR'])]
    for name, sig in conditions:
        st.write(f"- {name}: {'✅ 满足' if sig else '❌ 未满足'}")
    
    if all(c[1] for c in conditions):
        st.success("🎉 所有条件满足!")
    else:
        st.warning(f"⚠️ 满足 {sum(c[1] for c in conditions)}/3 个条件")

# Tab 3: CI
with tab3:
    st.header("📊 CI 复合指标")
    st.info("CI = ACI×0.4 + FPI×0.3 + LPR×0.3")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['CI'], fill='tozeroy', line=dict(width=3)))
    fig.add_hline(y=0.7, line_dash="dash", line_color="green", annotation_text="买入")
    fig.add_hline(y=0.3, line_dash="dash", line_color="red", annotation_text="卖出")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("成分分解")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_result['date'], y=df_result['I_ACI_dynamic']*0.4, name='ACI', stackgroup='one'))
    fig2.add_trace(go.Scatter(x=df_result['date'], y=df_result['I_FPI']*0.3, name='FPI', stackgroup='one'))
    fig2.add_trace(go.Scatter(x=df_result['date'], y=df_result['I_LPR']*0.3, name='LPR', stackgroup='one'))
    st.plotly_chart(fig2, use_container_width=True)

# Tab 4: 核心指标
with tab4:
    st.header("📉 核心三大指标")
    
    st.subheader("1. ACI")
    c1, c2 = st.columns(2)
    with c1: st.metric("原始ACI", f"{latest['aci_original']:.1f}月")
    with c2: st.metric("广义ACI", f"{latest['aci_extended']:.1f}月", delta=f"+{latest['aci_extended']-latest['aci_original']:.1f}")
    st.caption(f"广义={latest['inventory_area']:,.0f}+{latest['secondhand_area']:.0f}+{latest['auction_area']:.0f}")
    
    st.subheader("2. LPR")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("溢价率", f"{latest['premium_rate']:.1f}%")
    with c2: st.metric("溢价斜率", f"{latest['premium_slope']:.3f}")
    with c3: st.metric("均价斜率", f"{latest['land_price_slope']:.1f}")
    st.write("双轨制:" + ("✅" if latest['I_LPR'] else "❌"))
    
    st.subheader("3. FPI")
    st.metric("净融资", f"{latest['net_financing']:,.0f}亿")

# Tab 5: 未来预测
with tab5:
    st.header("🔮 未来底价估算")
    from src.models.predict_engine import PricePredictionEngine
    engine = PricePredictionEngine()
    engine.CHINA_ELASTICITY_COEFFICIENT = elasticity
    engine.current_decline_rate = current_decline
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("弹性系数", f"{elasticity}")
    with c2: st.metric("当前跌幅", f"{current_decline*100:.0f}%")
    with c3: st.metric("目标跌幅", f"{target_decline*100:.0f}%")
    with c4: st.metric("剩余空间", f"{(target_decline-current_decline)*100:.0f}%")
    
    macro = engine.get_macro_penalty_factors()
    st.subheader("宏观惩罚")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("老龄化", f"{macro['aging_rate']*100:.1f}%", f"惩罚{macro['aging_penalty']:.2f}x")
    with c2: st.metric("杠杆率", f"{macro['leverage_rate']*100:.0f}%", f"惩罚{macro['leverage_penalty']:.2f}x")
    with c3: st.metric("综合", f"{macro['combined_penalty']:.2f}x")
    
    curve = engine.predict_price_curve(36, 100, target_decline/36, True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve['date'], y=curve['price_pct'], line=dict(width=3), mode='lines+markers'))
    fig.add_hline(y=(1-target_decline)*100, line_dash="dot", line_color="red")
    fig.add_hline(y=(1-current_decline)*100, line_dash="dot", line_color="yellow")
    fig.update_layout(height=400, yaxis_range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)
    
    adjusted = policy_damping * macro['combined_penalty']
    bottom = engine.calculate_bottom_time(current_decline, target_decline, target_decline/36, adjusted)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("基础月数", f"{bottom['base_months_to_bottom']:.0f}")
    with c2: st.metric("阻尼", f"{bottom['policy_damping']:.2f}x")
    with c3: st.metric("调整后", f"{bottom['adjusted_months_to_bottom']:.0f}月")
    with c4: st.metric("底部", bottom['bottom_date'])

# Tab 6: 回测
with tab6:
    st.header("📈 历史回测")
    df_result['strategy'] = (df_result['CI'] >= 0.5).astype(int)
    df_result['returns'] = df_result['price'].pct_change()
    df_result['strategy_returns'] = df_result['strategy'].shift(1) * df_result['returns']
    cumulative = (1 + df_result['strategy_returns'].fillna(0)).cumprod()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_result['date'], y=cumulative, name='策略', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=df_result['date'], y=df_result['price']/df_result['price'].iloc[0], name='买入持有', line=dict(dash='dash')))
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.metric("总收益", f"{(cumulative.iloc[-1]-1)*100:.1f}%")

# Tab 7: 数据表
with tab7:
    st.header("📋 完整数据")
    cols = st.multiselect("列", df_result.columns.tolist(), 
                         default=['date', 'aci_original', 'aci_extended', 'net_financing', 'premium_rate', 'CI'])
    st.dataframe(df_result[cols], use_container_width=True)
