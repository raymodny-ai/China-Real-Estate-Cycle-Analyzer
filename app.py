"""
中国房地产周期分析仪表盘 — Streamlit Dashboard
China Real Estate Cycle Analyzer — app.py

改进:
    - 侧边栏: 日期范围、权重滑块、ACI 阈值、城市等级筛选
    - 6 个标签: 判断口诀 / CI 指数 / 三大指标 / 历史回测 / 中日对比 / 数据导出
    - 顶部预警横幅 (ACI 超过阈值)
    - 中日对比: 静态表 → 多维度动态折线图
    - 数据导出: CSV + Excel 下载
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.utils.config import get as cfg_get, load_config
from src.utils.db import get_engine
from src.services.cycle_analyzer import CycleAnalyzerService

# ─────────────────────────────────────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="中国房地产周期分析 | CI Model",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏘️ 中国房价底部预测模型 (CI Model)")
st.markdown("基于**库存去化 · 银行信用约束**量化框架，多维指标联合研判房价周期底部。")

# ─────────────────────────────────────────────────────────────────────────────
# 侧边栏控制面板
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 模型参数控制")

    st.subheader("1️⃣ 指标权重调整")
    st.caption("三项权重之和须等于 1.0")
    w_aci = st.slider("ACI 权重（去化周期）", 0.1, 0.7,
                      float(cfg_get("model.weights.aci", 0.4)), step=0.05, key="w_aci")
    w_fpi = st.slider("FPI 权重（资金链压力）", 0.1, 0.7,
                      float(cfg_get("model.weights.fpi", 0.3)), step=0.05, key="w_fpi")
    w_lpr = st.slider("LPR 权重（土地溢价率）", 0.1, 0.7,
                      float(cfg_get("model.weights.lpr", 0.3)), step=0.05, key="w_lpr")

    weight_sum = round(w_aci + w_fpi + w_lpr, 2)
    if abs(weight_sum - 1.0) > 0.01:
        st.warning(f"⚠️ 权重之和 = {weight_sum}（应为 1.0），结果仅供参考。")

    st.subheader("2️⃣ ACI 阈值调整")
    aci_limit = st.slider(
        "去化周期警戒线（月）",
        min_value=12, max_value=36,
        value=int(cfg_get("model.thresholds.aci_limit", 24)),
        step=1, key="aci_limit",
    )

    st.subheader("3️⃣ 城市等级")
    city_tier_opt = st.selectbox(
        "参考城市等级 ACI 阈值",
        options=["全国基准", "一线城市 (≤18月)", "二线城市 (≤24月)", "三四线城市 (≤30月)"],
        index=0,
        key="city_tier",
    )

    st.subheader("4️⃣ 日期范围")
    date_start = st.date_input("起始日期", value=pd.Timestamp("2013-01-01"), key="date_start")
    date_end   = st.date_input("结束日期", value=pd.Timestamp.today(), key="date_end")

    st.divider()
    recalc = st.button("🔄 重新计算 CI 指数", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# 实时计算 CI (如用户点击重新计算或权重变更)
# ─────────────────────────────────────────────────────────────────────────────
if recalc:
    with st.spinner("正在重新计算 CI 指数..."):
        analyzer = CycleAnalyzerService()
        analyzer.calculate_ci_index(w_aci=w_aci, w_fpi=w_fpi, w_lpr=w_lpr, aci_limit=aci_limit)
    st.success("✅ CI 指数已更新！")

# ─────────────────────────────────────────────────────────────────────────────
# 数据加载
# ─────────────────────────────────────────────────────────────────────────────
engine = get_engine()

@st.cache_data(ttl=3600)
def load_all_data() -> dict:
    """从数据库加载全部分析数据。"""
    tables = {
        "aci":  "macro_aci_data",
        "fpi":  "financial_fpi_data",
        "lpr":  "land_lpr_data",
        "ci":   "model_ci_index",
        "bt":   "backtest_results",
        "perf": "backtest_performance",
        "jp":   "japan_comparison",
    }
    result = {}
    for key, table in tables.items():
        try:
            result[key] = pd.read_sql(table, con=engine)
        except Exception:
            result[key] = pd.DataFrame()
    return result

with st.spinner("⏳ 正在加载底层数据，请稍候..."):
    data = load_all_data()

# ── 检查必要数据 ──────────────────────────────────────────────────────────────
if data["ci"].empty or data["aci"].empty:
    st.error("⚠️ 数据库中未找到数据。请先运行：`python src/data_fetchers/run_all.py` 和 `python src/models/indicators.py`")
    st.stop()

# ── 解析日期 + 过滤范围 ──────────────────────────────────────────────────────
for key in ["aci", "fpi", "lpr", "ci", "bt"]:
    if not data[key].empty and "date" in data[key].columns:
        data[key]["date"] = pd.to_datetime(data[key]["date"])
        mask = (data[key]["date"] >= pd.Timestamp(date_start)) & \
               (data[key]["date"] <= pd.Timestamp(date_end))
        data[key] = data[key][mask].copy()

ci_df  = data["ci"]
aci_df = data["aci"]
fpi_df = data["fpi"]
lpr_df = data["lpr"]
bt_df  = data["bt"]
jp_df  = data["jp"]

# ─────────────────────────────────────────────────────────────────────────────
# 顶部预警横幅
# ─────────────────────────────────────────────────────────────────────────────
if not ci_df.empty:
    latest = ci_df.merge(aci_df[["date", "aci"]], on="date", how="left").iloc[-1] \
             if "aci" not in ci_df.columns else ci_df.iloc[-1]
    analyzer = CycleAnalyzerService()
    alerts = analyzer.evaluate_alerts(latest)
    for alert in alerts:
        if alert["level"] == "danger":
            st.error(alert["message"])
        elif alert["level"] == "warning":
            st.warning(alert["message"])
        else:
            st.info(alert["message"])

# ─────────────────────────────────────────────────────────────────────────────
# 标签页
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 判断口诀与现状",
    "📈 CI 复合指数",
    "🔍 核心三大指标",
    "🧪 历史回测",
    "🗾 中日对比",
    "💾 数据导出",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — 判断口诀与现状
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("底部确认判断口诀")
    st.markdown(
        "**逻辑链条**：`需求端萎缩` → `库存堆高` → `现金流紧张` → `银行收缩` → `土地流拍` → `价格触底`"
    )

    if ci_df.empty:
        st.warning("暂无 CI 数据。")
    else:
        latest_ci = ci_df.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)

        cond1 = "✅ 满足" if latest_ci.get("I_ACI", 0) == 1 else "❌ 未满足"
        cond2 = "✅ 满足" if latest_ci.get("I_FPI", 0) == 1 else "❌ 未满足"
        cond3 = "✅ 满足" if latest_ci.get("I_LPR", 0) == 1 else "❌ 未满足"
        ci_val = float(latest_ci.get("CI", 0))
        ci_pct = f"{ci_val:.0%}"

        c1.metric("1. 库存 < 警戒线 (ACI)", cond1)
        c2.metric("2. 融资转正 (FPI)", cond2)
        c3.metric("3. 土地回暖 (LPR)", cond3)
        c4.metric("综合 CI 指数", ci_pct,
                  delta="强信号" if ci_val >= 0.7 else ("弱信号" if ci_val >= 0.3 else "无信号"))

        # Gauge 仪表盘
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=ci_val * 100,
            title={"text": "CI 底部信号强度 (%)"},
            delta={"reference": 50},
            gauge={
                "axis": {"range": [0, 100]},
                "bar":  {"color": "#1f77b4"},
                "steps": [
                    {"range": [0, 30],  "color": "#d62728"},
                    {"range": [30, 70], "color": "#ff7f0e"},
                    {"range": [70, 100],"color": "#2ca02c"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 3},
                    "thickness": 0.75, "value": 70,
                },
            },
        ))
        fig_gauge.update_layout(height=280)
        st.plotly_chart(fig_gauge, use_container_width=True)

        # 结论
        st.subheader("现状结论")
        all_met = all(latest_ci.get(f"I_{x}", 0) == 1 for x in ["ACI", "FPI", "LPR"])
        if all_met:
            st.success("✅ **确认**：三大底部条件已同时满足，底部特征完整显现。")
        else:
            cnt = sum(latest_ci.get(f"I_{x}", 0) for x in ["ACI", "FPI", "LPR"])
            st.warning(f"⚠️ **现状**：{cnt}/3 个底部条件已满足，仍需等待更多信号共振。")

        # 城市分级评估
        if "aci" in ci_df.columns:
            aci_val = float(latest_ci.get("aci", 0))
        elif not aci_df.empty:
            aci_val = float(aci_df.iloc[-1]["aci"])
        else:
            aci_val = 0.0

        if aci_val > 0:
            st.subheader("城市分级 ACI 评估")
            analyzer = CycleAnalyzerService()
            tier_eval = analyzer.evaluate_city_tier_aci(aci_val)
            cols = st.columns(3)
            for i, tier_info in enumerate(tier_eval):
                status_map = {"ok": "✅ 安全", "warning": "🟡 预警", "danger": "🔴 超线"}
                cols[i].metric(
                    label=tier_info["label"],
                    value=status_map[tier_info["status"]],
                    delta=f"ACI {aci_val:.1f}月 / 阈值 {tier_info['limit']}月",
                )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CI 复合指数
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("CI 复合研判指数 (Composite Index)")
    st.markdown(
        "CI 由三个子条件加权构成。三大信号同时触发时 CI 上升，预示底部共振最强。  \n"
        f"当前权重 — **ACI: {w_aci}  |  FPI: {w_fpi}  |  LPR: {w_lpr}**"
    )

    if ci_df.empty:
        st.warning("暂无 CI 数据。")
    else:
        # 主线图（带颜色分区）
        fig_ci = go.Figure()
        fig_ci.add_trace(go.Scatter(
            x=ci_df["date"], y=ci_df["CI"],
            mode="lines", name="CI 指数",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy", fillcolor="rgba(31,119,180,0.12)",
        ))
        fig_ci.add_hline(y=0.7, line_dash="dot", line_color="green",
                         annotation_text="0.7 强信号区")
        fig_ci.add_hline(y=0.3, line_dash="dot", line_color="orange",
                         annotation_text="0.3 弱信号区")
        fig_ci.update_layout(
            title="CI 复合指标动态走势",
            xaxis_title="日期", yaxis_title="CI 值",
            yaxis=dict(range=[0, 1.05]),
            height=400,
        )
        st.plotly_chart(fig_ci, use_container_width=True)

        # 历史分布直方图
        col_hist, col_stat = st.columns([2, 1])
        with col_hist:
            fig_hist = px.histogram(
                ci_df, x="CI", nbins=20,
                title="CI 历史分布",
                color_discrete_sequence=["#1f77b4"],
            )
            fig_hist.update_layout(height=300)
            st.plotly_chart(fig_hist, use_container_width=True)
        with col_stat:
            st.subheader("CI 统计摘要")
            st.dataframe(
                ci_df["CI"].describe().rename("CI 值").to_frame().round(3),
                use_container_width=True,
            )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — 核心三大指标
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("核心三大指标详情")

    # ── ACI ──────────────────────────────────────────────────────────────────
    st.subheader("1. 去化周期 ACI（月度）")
    if not aci_df.empty:
        fig_aci = go.Figure()
        fig_aci.add_trace(go.Scatter(
            x=aci_df["date"], y=aci_df["aci"],
            name="去化周期 ACI", mode="lines",
            line=dict(color="#1f77b4"),
        ))
        # 警戒线（基准 + 城市分级）
        tier_colors = {"tier1": "#EF553B", "tier2": "#FFA15A", "tier3": "#FF6692"}
        tier_labels = {"tier1": "一线 (18月)", "tier2": "二线 (24月)", "tier3": "三四线 (30月)"}
        tier_vals   = {"tier1": 18, "tier2": 24, "tier3": 30}
        for tk, tv in tier_vals.items():
            fig_aci.add_hline(
                y=tv, line_dash="dash",
                line_color=tier_colors[tk],
                annotation_text=tier_labels[tk],
            )
        fig_aci.update_layout(title="可售库存 / 月均销售面积 (ACI)", xaxis_title="日期",
                              yaxis_title="月数", height=420)
        st.plotly_chart(fig_aci, use_container_width=True)
    else:
        st.info("ACI 数据暂无。")

    # ── FPI ──────────────────────────────────────────────────────────────────
    st.subheader("2. 房企资金链压力指数 FPI")
    st.caption("⚠️ FPI 为年度数据（来源：年报净融资现金流），图中前向填充至月度，仅为展示连续性。")
    if not fpi_df.empty:
        fig_fpi = go.Figure()
        fig_fpi.add_trace(go.Bar(
            x=fpi_df["date"], y=fpi_df["net_financing_cash_flow"],
            name="净融资额",
            marker_color=["#2ca02c" if v > 0 else "#d62728"
                          for v in fpi_df["net_financing_cash_flow"]],
        ))
        fig_fpi.add_hline(y=0, line_dash="dot", line_color="black",
                          annotation_text="资金转正红线")
        fig_fpi.update_layout(title="核心房企净融资额度（年度指标）",
                              xaxis_title="年份", yaxis_title="万元", height=380)
        st.plotly_chart(fig_fpi, use_container_width=True)
    else:
        st.info("FPI 数据暂无。")

    # ── LPR ──────────────────────────────────────────────────────────────────
    st.subheader("3. 土地溢价拍买率 LPR")
    if not lpr_df.empty:
        lpr_df["lpr_ma6"] = lpr_df["premium_rate"].rolling(6).mean()
        fig_lpr = go.Figure()
        fig_lpr.add_trace(go.Scatter(
            x=lpr_df["date"], y=lpr_df["premium_rate"],
            name="溢价率", mode="lines",
            line=dict(color="#aec7e8", width=1), opacity=0.7,
        ))
        fig_lpr.add_trace(go.Scatter(
            x=lpr_df["date"], y=lpr_df["lpr_ma6"],
            name="6个月MA", mode="lines",
            line=dict(color="#1f77b4", width=2.5),
        ))
        fig_lpr.add_hline(y=5, line_dash="dash", line_color="orange",
                          annotation_text="5% 荣枯线")
        fig_lpr.update_layout(title="土地溢价率走势 + 6个月均线",
                              xaxis_title="日期", yaxis_title="%", height=400)
        st.plotly_chart(fig_lpr, use_container_width=True)
    else:
        st.info("LPR 数据暂无。")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — 历史回测
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("CI 与房价指数关系回测")

    # 绩效指标卡片
    perf_df = data.get("perf", pd.DataFrame())
    if not perf_df.empty:
        perf = perf_df.iloc[0]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("最大回撤",  f"{float(perf.get('max_drawdown_pct', 0)):.1f}%")
        k2.metric("年化夏普",  f"{float(perf.get('annualized_sharpe', 0)):.2f}")
        k3.metric("CI信号命中率", f"{float(perf.get('ci_signal_hit_rate', 0)):.1%}")
        k4.metric("当前 HPI",  f"{float(perf.get('current_hpi', 0)):.1f}")
    else:
        st.info("绩效统计暂无。请先运行 `python src/models/backtest.py`")

    if not bt_df.empty:
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(
            x=bt_df["date"], y=bt_df["HPI"],
            mode="lines", name="模拟 HPI",
            line=dict(color="#2ca02c", width=2),
        ))
        fig_bt.add_trace(go.Scatter(
            x=bt_df["date"], y=bt_df["CI"] * 100,
            mode="lines", name="CI × 100",
            line=dict(color="#d62728", width=1.5, dash="dot"),
            yaxis="y2",
        ))
        fig_bt.update_layout(
            title="CI 触发与模拟房价指数的负反馈推演",
            xaxis_title="日期",
            yaxis=dict(title="HPI"),
            yaxis2=dict(title="CI × 100", overlaying="y", side="right"),
            legend=dict(x=0.01, y=0.99),
            height=450,
        )
        # 政策冲击标注
        fig_bt.add_vrect(
            x0="2015-01-01", x1="2017-06-01",
            fillcolor="rgba(44,160,44,0.12)", opacity=0.5,
            annotation_text="去库存政策", annotation_position="top left",
        )
        fig_bt.add_vrect(
            x0="2021-01-01", x1="2022-12-01",
            fillcolor="rgba(214,39,40,0.12)", opacity=0.5,
            annotation_text="监管收紧", annotation_position="top left",
        )
        st.plotly_chart(fig_bt, use_container_width=True)
    else:
        st.info("回测数据暂无。请先运行 `python src/models/backtest.py`")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — 中日对比
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("中日房地产周期对比")
    st.markdown("以各自**泡沫顶峰**为 T+0，对齐两国多维度指标走势。")

    if not jp_df.empty:
        dim_options = {
            "房价指数（顶峰=100）": "house_price_index",
            "城镇化率 (%)":         "urbanization_rate",
            "老龄化率（65岁以上 %）": "aging_rate",
            "家庭负债率 / GDP (%)": "household_debt_gdp",
        }
        selected_dim = st.radio(
            "选择对比维度",
            options=list(dim_options.keys()),
            horizontal=True,
        )
        col_name = dim_options[selected_dim]

        fig_jp = px.line(
            jp_df, x="year_label", y=col_name,
            color="country",
            markers=True,
            labels={"year_label": "距顶峰年数 (T)", col_name: selected_dim},
            title=f"中日对比：{selected_dim}",
            color_discrete_map={
                "Japan (1991 顶峰)": "#d62728",
                "China (2021 顶峰)": "#1f77b4",
            },
        )
        fig_jp.add_vline(x=6, line_dash="dash", line_color="gray",
                         annotation_text="顶峰 T+0")
        fig_jp.update_layout(height=460)
        st.plotly_chart(fig_jp, use_container_width=True)

        # 关键特征对比表
        st.subheader("关键参数对比")
        compare_table = pd.DataFrame({
            "维度":          ["泡沫顶峰年份", "顶峰后最大跌幅", "城镇化率（顶峰）", "老龄化率（顶峰）", "家庭负债/GDP（顶峰）", "弹性系数估算"],
            "日本 (1991)":  ["1991", "-80%", "~77%", "~12%", "~75%", "–"],
            "中国 (2021)":  ["2021", "-30%（截至今）", "~65%", "~14%", "~62%", "1.05（估算）"],
        })
        st.dataframe(compare_table, use_container_width=True, hide_index=True)

        st.markdown("""
        **中国特殊性分析**：  
        1. 城镇化率仍有提升空间（日本顶峰时更高），为需求提供一定支撑。  
        2. 老龄化速度更快（人口结构劣势），与家庭债务叠加形成双重压力。  
        3. 政策调控力度更强（限价、保交楼、城中村改造），下跌曲线可能更平缓。  
        """)
    else:
        st.info("日本对比数据暂无。请先运行 `python src/models/backtest.py`")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — 数据导出
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("💾 数据导出")
    st.markdown("下载各模块数据至本地（CSV / Excel 格式）。")

    export_map: dict[str, pd.DataFrame] = {
        "CI 复合指数 (ci_index)":    ci_df,
        "去化周期 ACI (macro_aci)":  aci_df,
        "资金链压力 FPI (fpi)":       fpi_df,
        "土地溢价率 LPR (lpr)":       lpr_df,
        "回测结果 (backtest)":        bt_df,
        "中日对比 (japan)":           jp_df,
    }

    for label, df in export_map.items():
        if df.empty:
            continue
        col_dl1, col_dl2, col_info = st.columns([1, 1, 4])
        # CSV
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        col_dl1.download_button(
            label="CSV",
            data=csv_bytes,
            file_name=f"{label.split('(')[-1].rstrip(')')}.csv",
            mime="text/csv",
            key=f"csv_{label}",
        )
        # Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        col_dl2.download_button(
            label="Excel",
            data=buffer.getvalue(),
            file_name=f"{label.split('(')[-1].rstrip(')')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xlsx_{label}",
        )
        col_info.markdown(f"**{label}** — {len(df):,} 行 × {len(df.columns)} 列")

    st.divider()
    st.caption("提示：所有数据均基于模拟生成（参见各数据模块说明）。如需真实数据请接入相应 API。")
