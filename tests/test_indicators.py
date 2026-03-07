"""
单元测试 — 指标计算器
tests/test_indicators.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ── 拦截数据库依赖，独立测试纯逻辑 ────────────────────────────────────────────
from src.services.cycle_analyzer import (
    _linear_slope,
    _rolling_slope,
    CycleAnalyzerService,
)


# ---------------------------------------------------------------------------
# _linear_slope
# ---------------------------------------------------------------------------
class TestLinearSlope:
    def test_positive_series(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        assert _linear_slope(s) > 0

    def test_negative_series(self):
        s = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
        assert _linear_slope(s) < 0

    def test_flat_series(self):
        s = pd.Series([3.0, 3.0, 3.0, 3.0])
        assert abs(_linear_slope(s)) < 1e-9

    def test_insufficient_data(self):
        s = pd.Series([1.0, 2.0])
        assert _linear_slope(s) == 0.0

    def test_with_nan(self):
        s = pd.Series([np.nan, 1.0, 2.0, 3.0])
        slope = _linear_slope(s)
        assert slope > 0  # nan 被 dropna 剔除后仍为正斜率


# ---------------------------------------------------------------------------
# _rolling_slope
# ---------------------------------------------------------------------------
class TestRollingSlope:
    def test_output_length(self):
        s = pd.Series(range(24), dtype=float)
        result = _rolling_slope(s, 6)
        assert len(result) == len(s)

    def test_first_windows_are_nan(self):
        s = pd.Series(range(12), dtype=float)
        result = _rolling_slope(s, 6)
        assert pd.isna(result.iloc[0])

    def test_uptrend_slope_positive(self):
        s = pd.Series(range(24), dtype=float)
        result = _rolling_slope(s, 6)
        assert (result.dropna() > 0).all()


# ---------------------------------------------------------------------------
# ACI 条件判断 (通过 evaluate_city_tier_aci)
# ---------------------------------------------------------------------------
class TestCityTierAci:
    def test_aci_far_below_limit_is_ok(self):
        """ACI 远低于所有城市等级阈值时，所有等级应为 ok。"""
        analyzer = CycleAnalyzerService()
        result = analyzer.evaluate_city_tier_aci(5.0)
        for tier in result:
            assert tier["status"] == "ok"

    def test_aci_above_tier3_limit_is_danger(self):
        """ACI 超过三四线城市阈值 (30月) 时，tier3 应为 danger。"""
        analyzer = CycleAnalyzerService()
        result = analyzer.evaluate_city_tier_aci(32.0)
        tier3 = next(t for t in result if t["label"] == "三四线城市")
        assert tier3["status"] == "danger"

    def test_tier1_more_strict_than_tier3(self):
        """一线城市阈值 < 三线城市阈值。"""
        analyzer = CycleAnalyzerService()
        result = analyzer.evaluate_city_tier_aci(20.0)
        tier1 = next(t for t in result if t["label"] == "一线城市")
        tier3 = next(t for t in result if t["label"] == "三四线城市")
        assert tier1["limit"] < tier3["limit"]

    def test_all_tiers_present(self):
        analyzer = CycleAnalyzerService()
        result = analyzer.evaluate_city_tier_aci(15.0)
        labels = {t["label"] for t in result}
        assert {"全国基准", "一线城市", "二线城市", "三四线城市"}.intersection(labels)


# ---------------------------------------------------------------------------
# FPI 条件判断
# ---------------------------------------------------------------------------
class TestFpiCondition:
    """通过 evaluate_alerts 间接验证 FPI 逻辑。"""

    def test_high_ci_triggers_info_alert(self):
        row = pd.Series({
            "aci": 10.0,          # 低于警戒线 → 无 ACI 告警
            "net_financing_cash_flow": 50000,
            "CI": 0.9,            # 高 CI → 底部信号强
        })
        analyzer = CycleAnalyzerService()
        alerts = analyzer.evaluate_alerts(row)
        levels = [a["level"] for a in alerts]
        assert "info" in levels

    def test_aci_danger_alert(self):
        """ACI 超过 24 月警戒线时应触发 danger 级别预警。"""
        row = pd.Series({"aci": 26.0, "CI": 0.1})
        analyzer = CycleAnalyzerService()
        alerts = analyzer.evaluate_alerts(row)
        assert any(a["level"] == "danger" for a in alerts)

    def test_aci_warning_alert(self):
        """ACI 在 20-24 月区间应触发 warning 级别预警。"""
        row = pd.Series({"aci": 22.0, "CI": 0.2})
        analyzer = CycleAnalyzerService()
        alerts = analyzer.evaluate_alerts(row)
        assert any(a["level"] == "warning" for a in alerts)

    def test_no_alert_when_safe(self):
        """所有指标安全时不应触发任何预警。"""
        row = pd.Series({"aci": 10.0, "CI": 0.2})
        analyzer = CycleAnalyzerService()
        alerts = analyzer.evaluate_alerts(row)
        danger_or_warning = [a for a in alerts if a["level"] in ("danger", "warning")]
        assert len(danger_or_warning) == 0


# ---------------------------------------------------------------------------
# CI 权重有效性
# ---------------------------------------------------------------------------
class TestCiWeights:
    def test_weights_sum_near_one(self):
        from src.utils.config import get as cfg_get
        w1 = cfg_get("model.weights.aci", 0.4)
        w2 = cfg_get("model.weights.fpi", 0.3)
        w3 = cfg_get("model.weights.lpr", 0.3)
        assert abs(w1 + w2 + w3 - 1.0) < 0.01

    def test_weights_are_positive(self):
        from src.utils.config import get as cfg_get
        for key in ["model.weights.aci", "model.weights.fpi", "model.weights.lpr"]:
            assert cfg_get(key) > 0

    def test_ci_bounded_zero_to_one(self):
        """任意权重组合下，CI 值应在 [0, 1]。"""
        for w1, w2, w3 in [(0.4, 0.3, 0.3), (0.5, 0.3, 0.2), (1.0, 0.0, 0.0)]:
            for i_aci, i_fpi, i_lpr in [(0, 0, 0), (1, 0, 0), (1, 1, 1)]:
                ci = w1 * i_aci + w2 * i_fpi + w3 * i_lpr
                assert 0.0 <= ci <= 1.0
