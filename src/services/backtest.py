"""
历史回测与中日对比 — Backtest & Japan Comparison Service
对 CI 指数与房价指数的历史关联性进行推演。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Optional, Any
from sqlalchemy import Engine

from src.utils.db import get_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestService:
    """提供历史回测与比较服务的类。"""
    
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or get_engine()

    def _simulate_hpi(self, n: int, ci_values: np.ndarray) -> np.ndarray:
        """生成模拟房价指数 (HPI)。"""
        t = np.arange(n)
        base = 100 * np.exp(0.004 * t)
        
        shock = np.zeros(n)
        if n > 36:
            shock[36:min(36 + 18, n)] += 0.008 * np.arange(min(18, n - 36))
            
        if n > 96:
            shock[96:min(96 + 24, n)] -= 0.006 * np.arange(min(24, n - 96))
            
        ci_pressure = 0.18 * ci_values
        noise = np.random.normal(0, 1.2, n)
        hpi = base * (1 - ci_pressure) * (1 + shock) + noise
        return np.maximum(hpi, 30.0)

    def _max_drawdown(self, series: pd.Series) -> float:
        """计算序列最大回撤（负数表示下行）。"""
        roll_max = series.cummax()
        drawdown = (series - roll_max) / roll_max
        return float(drawdown.min())

    def _sharpe_ratio(self, returns: pd.Series, annualize: int = 12) -> float:
        """计算年化夏普比率（无风险利率设为 0）。"""
        if returns.std() == 0:
            return 0.0
        return float(returns.mean() / returns.std() * np.sqrt(annualize))

    def _signal_hit_rate(self, ci: pd.Series, hpi_return: pd.Series, threshold: float = 0.5) -> float:
        """计算 CI 信号命中率。"""
        signal_months = ci >= threshold
        if signal_months.sum() == 0:
            return 0.0
        correct = (hpi_return.shift(-1)[signal_months] > 0).sum()
        return float(correct / signal_months.sum())

    def run_backtest(self) -> Optional[pd.DataFrame]:
        """模拟历史 HPI 走势，并与 CI 指数进行对比回测分析。"""
        try:
            ci_df = pd.read_sql("model_ci_index", con=self.engine)
        except Exception as e:
            logger.error(f"读取 CI 指数失败: {e}")
            return None

        if ci_df.empty:
            logger.warning("CI 指数为空，回测中止。")
            return None

        ci_df["date"] = pd.to_datetime(ci_df["date"])
        n = len(ci_df)
        ci_values = ci_df["CI"].fillna(0).values

        logger.info(f"开始回测，共 {n} 个月度数据点")

        ci_df["HPI"] = self._simulate_hpi(n, ci_values)
        ci_df["HPI_Return"] = ci_df["HPI"].pct_change()

        peak_hpi = ci_df["HPI"].max()
        current_hpi = ci_df["HPI"].iloc[-1]
        drawdown = self._max_drawdown(ci_df["HPI"])
        sharpe = self._sharpe_ratio(ci_df["HPI_Return"].dropna())
        hit_rate = self._signal_hit_rate(ci_df["CI"], ci_df["HPI_Return"])

        logger.info(
            f"回测绩效 — 峰值 HPI: {peak_hpi:.1f} | 最新 HPI: {current_hpi:.1f} | "
            f"最大回撤: {drawdown:.2%} | 夏普: {sharpe:.2f} | CI 信号命中率: {hit_rate:.2%}"
        )

        perf = pd.DataFrame([{
            "peak_hpi":          peak_hpi,
            "current_hpi":       current_hpi,
            "max_drawdown_pct":  drawdown * 100,
            "annualized_sharpe": sharpe,
            "ci_signal_hit_rate": hit_rate,
        }])
        perf.to_sql("backtest_performance", con=self.engine, if_exists="replace", index=False)

        ci_df.to_sql("backtest_results", con=self.engine, if_exists="replace", index=False)
        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_backtest_results_date ON backtest_results (date)"))
                conn.commit()
        except Exception as e:
            logger.warning(f"无法建立索引 (backtest_results): {e}")
        logger.info("回测结果已保存至数据库 [backtest_results] 和 [backtest_performance]。")
        return ci_df

    def get_japanese_comparison(self) -> pd.DataFrame:
        """生成中日房地产泡沫破裂的关键维度时间序列对比数据。"""
        n_years = 21

        offsets = np.arange(-6, n_years - 6)
        jp_hpi        = 100 * np.exp(-0.08 * np.maximum(offsets, 0))
        jp_hpi[:6]    = np.linspace(40, 100, 6)
        jp_urban      = np.clip(63 + 0.3 * (offsets + 6), 63, 79)
        jp_aging      = np.clip(10 + 0.8 * (offsets + 6), 10, 26)
        jp_debt       = np.clip(55 + 1.5 * (offsets + 6) - 0.3 * np.maximum(offsets, 0) ** 1.5, 30, 85)

        japan_df = pd.DataFrame({
            "country":            "Japan (1991 顶峰)",
            "year_offset":        offsets,
            "year_label":         [f"T{o:+d}" for o in offsets],
            "house_price_index":  jp_hpi,
            "urbanization_rate":  jp_urban,
            "aging_rate":         jp_aging,
            "household_debt_gdp": jp_debt,
        })

        cn_offsets    = np.arange(-6, n_years - 6)
        cn_hpi        = 100 * np.exp(-0.04 * np.maximum(cn_offsets, 0))
        cn_hpi[:6]    = np.linspace(55, 100, 6)
        cn_urban      = np.clip(58 + 0.9 * (cn_offsets + 6), 58, 76)
        cn_aging      = np.clip(10 + 0.9 * (cn_offsets + 6), 10, 28)
        cn_debt       = np.clip(50 + 2.0 * (cn_offsets + 6) - 0.5 * np.maximum(cn_offsets, 0) ** 1.3, 30, 90)

        china_df = pd.DataFrame({
            "country":            "China (2021 顶峰)",
            "year_offset":        cn_offsets,
            "year_label":         [f"T{o:+d}" for o in cn_offsets],
            "house_price_index":  cn_hpi,
            "urbanization_rate":  cn_urban,
            "aging_rate":         cn_aging,
            "household_debt_gdp": cn_debt,
        })

        df = pd.concat([japan_df, china_df], ignore_index=True)

        df.to_sql("japan_comparison", con=self.engine, if_exists="replace", index=False)
        logger.info(f"中日对比时间序列数据已保存 [japan_comparison]，共 {len(df)} 条。")
        return df

if __name__ == "__main__":
    service = BacktestService()
    service.run_backtest()
    service.get_japanese_comparison()
