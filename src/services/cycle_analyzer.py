"""
周期研判服务 — Cycle Analyzer Service
读取 ACI / FPI / LPR 数据，计算 CI 复合研判指数。
升级为类模式，方便进行依赖注入和生命周期管理，并结合 Pydantic 进行类型校验。
"""
from __future__ import annotations

import logging
import warnings
from typing import Dict, Optional, List, Literal

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import Engine

from src.utils.config import get as cfg_get, load_config
from src.utils.db import get_engine
from src.utils.logger import get_logger
from src.schemas.models import CIResultSchema

warnings.filterwarnings("ignore")
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _linear_slope(series: pd.Series) -> float:
    """计算线性回归斜率"""
    s = series.dropna()
    if len(s) < 3:
        return 0.0
    x = np.arange(len(s))
    slope, _, _, _, _ = stats.linregress(x, s.values)
    return float(slope)


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """计算滚动线性回归斜率"""
    return series.rolling(window).apply(
        lambda w: _linear_slope(pd.Series(w)), raw=False
    )


# ---------------------------------------------------------------------------
# 核心服务类
# ---------------------------------------------------------------------------

class CycleAnalyzerService:
    """周期研判业务逻辑服务"""

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or get_engine()

    def calculate_ci_index(
        self,
        w_aci: Optional[float] = None,
        w_fpi: Optional[float] = None,
        w_lpr: Optional[float] = None,
        aci_limit: Optional[float] = None,
    ) -> Optional[pd.DataFrame]:
        """
        从数据库读取数据，计算并保存 CI 复合研判指数。
        """
        w1 = w_aci if w_aci is not None else cfg_get("model.weights.aci", 0.4)
        w2 = w_fpi if w_fpi is not None else cfg_get("model.weights.fpi", 0.3)
        w3 = w_lpr if w_lpr is not None else cfg_get("model.weights.lpr", 0.3)

        aci_thresh = aci_limit if aci_limit is not None else cfg_get("model.thresholds.aci_limit", 24)
        fpi_thresh = cfg_get("model.thresholds.fpi_positive_level", 0)
        lpr_ma_win = int(cfg_get("model.thresholds.lpr_ma_window", 6))
        lpr_sl_win = int(cfg_get("model.thresholds.lpr_slope_window", 6))

        logger.info(
            f"CI 计算参数 — 权重: ACI={w1}, FPI={w2}, LPR={w3} | "
            f"阈值: ACI<{aci_thresh}月, FPI>{fpi_thresh}, LPR MA窗口={lpr_ma_win}月"
        )

        try:
            aci_df = pd.read_sql("macro_aci_data", con=self.engine)
            fpi_df = pd.read_sql("financial_fpi_data", con=self.engine)
            lpr_df = pd.read_sql("land_lpr_data", con=self.engine)
        except Exception as e:
            logger.error(f"读取数据库失败: {e}")
            raise RuntimeError(f"数据库读取失败: {e}") from e

        for df, name in [(aci_df, "ACI"), (fpi_df, "FPI"), (lpr_df, "LPR")]:
            if df.empty:
                logger.warning(f"{name} 数据为空，请先运行数据获取脚本")
                
            df["date"] = pd.to_datetime(df["date"])
            df["year_month"] = df["date"].dt.to_period("M")

        start = cfg_get("data.start_date", "2013-01-01")
        all_months = pd.date_range(
            start=start, 
            end=pd.Timestamp.today().normalize(), 
            freq="ME"
        ).to_period("M")
        master_df = pd.DataFrame({"year_month": all_months})

        if not fpi_df.empty:
            fpi_monthly = (
                fpi_df.set_index("year_month")[["net_financing_cash_flow"]]
                .resample("M")
                .ffill()
                .reset_index()
            )
            fpi_monthly = fpi_monthly.drop_duplicates("year_month", keep="last")
        else:
            fpi_monthly = pd.DataFrame(columns=["year_month", "net_financing_cash_flow"])

        master_df = master_df.merge(aci_df[["year_month", "aci"]] if not aci_df.empty else pd.DataFrame(columns=["year_month", "aci"]), on="year_month", how="left")
        master_df = master_df.merge(fpi_monthly, on="year_month", how="left")
        master_df = master_df.merge(lpr_df[["year_month", "premium_rate"]] if not lpr_df.empty else pd.DataFrame(columns=["year_month", "premium_rate"]), on="year_month", how="left")
        master_df = master_df.ffill().bfill()

        master_df["I_ACI"] = (master_df["aci"] < aci_thresh).astype(int)
        master_df["I_FPI"] = (master_df["net_financing_cash_flow"] > fpi_thresh).astype(int)

        ma = master_df["premium_rate"].rolling(lpr_ma_win).mean()
        slope = _rolling_slope(master_df["premium_rate"], lpr_sl_win)
        master_df["I_LPR"] = ((ma > ma.shift(1)) & (slope > 0)).astype(int)
        master_df["I_LPR"] = master_df["I_LPR"].fillna(0)

        master_df["CI"] = (
            w1 * master_df["I_ACI"] 
            + w2 * master_df["I_FPI"] 
            + w3 * master_df["I_LPR"]
        )
        master_df["weights_used"] = f"ACI={w1},FPI={w2},LPR={w3}"

        master_df["date"] = master_df["year_month"].dt.to_timestamp()
        master_df = master_df.drop(columns=["year_month"])
        
        # Validation mapping via repository layer (optional, but good practice)
        try:
            from src.repository.base import RepositoryFactory
            repo = RepositoryFactory.create("ci", self.engine)
            repo.save(master_df)
        except Exception as e:
            logger.error(f"保存 CI 指数失败 (可能是 Pydantic 校验未通过或是直接的 DB Error): {e}")
            try:
                master_df.to_sql("model_ci_index", con=self.engine, if_exists="replace", index=False)
            except Exception as inner_e:
                raise inner_e from e

        if not master_df.empty:
            latest = master_df.iloc[-1]
            logger.info(
                f"CI 计算完毕。最新值: CI={latest['CI']:.2f} | ACI={latest['aci']:.1f}月"
            )
        
        return master_df

    def evaluate_city_tier_aci(self, aci_value: float) -> list[dict]:
        """
        按城市分级评估当前 ACI 值相对各城市等级的阈值状况。
        """
        tiers = self.config.get("city_tiers", {})
        result = []
        for tier_key, tier_cfg in tiers.items():
            limit = tier_cfg.get("aci_limit", 24)
            warning = tier_cfg.get("aci_warning", 20)
            label = tier_cfg.get("label", tier_key)
            if aci_value >= limit: status = "danger"
            elif aci_value >= warning: status = "warning"
            else: status = "ok"
            result.append({"label": label, "status": status, "limit": limit, "warning": warning, "aci": aci_value})
        return result

    def evaluate_alerts(self, latest_row: pd.Series) -> list[dict]:
        """
        根据最新指标行检测并返回所有触发的预警列表。
        """
        alerts = []
        aci_limit = cfg_get("model.thresholds.aci_limit", 24)
        aci_warning = cfg_get("model.thresholds.aci_warning", 20)
        ci_high = cfg_get("alerts.ci_high_threshold", 0.7)
        aci_val = float(latest_row.get("aci", 0))
        ci_val = float(latest_row.get("CI", 0))

        if aci_val >= aci_limit:
            alerts.append({"level": "danger", "message": f"🔴 去化周期 {aci_val:.1f} 月已超过警戒线 {aci_limit} 月！库存严峻。"})
        elif aci_val >= aci_warning:
            alerts.append({"level": "warning", "message": f"🟡 去化周期 {aci_val:.1f} 月接近警戒线（{aci_warning}→{aci_limit} 月预警区间）。"})
        if ci_val >= ci_high:
            alerts.append({"level": "info", "message": f"🟢 CI 指数 {ci_val:.2f} 高于 {ci_high}，底部信号较强，多项指标同向改善。"})

        return alerts

    def get_latest_ci(self) -> Optional[CIResultSchema]:
        """获取最新的 CI 计算结果并以此 Schema 返回"""
        try:
            df = pd.read_sql("model_ci_index", con=self.engine)
            if df.empty:
                return None
                
            latest = df.iloc[-1]
            ci_val = float(latest["CI"])
            
            if ci_val >= 0.7:
                status: Literal["strong", "weak", "none"] = "strong"
            elif ci_val >= 0.3:
                status = "weak"
            else:
                status = "none"
            
            result_dict = {
                "date": pd.to_datetime(latest["date"]),
                "ci": ci_val,
                "i_aci": int(latest["I_ACI"]),
                "i_fpi": int(latest["I_FPI"]),
                "i_lpr": int(latest["I_LPR"]),
                "weights": str(latest.get("weights_used", "")),
                "status": status,
            }
            
            return CIResultSchema(**result_dict)
        except Exception as e:
            logger.error(f"获取最新 CI 失败: {e}")
            return None
