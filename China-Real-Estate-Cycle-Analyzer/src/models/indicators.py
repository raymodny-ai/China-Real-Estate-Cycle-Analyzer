"""
CI 指标计算模块 (优化版)
包含动态阈值判断逻辑

优化内容：
1. ACI 动态阈值：使用滚动5年均值判断
2. LPR 双轨制：土地溢价率 + 土地均价斜率
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple


class IndicatorCalculator:
    """
    指标计算器
    核心功能：
    - 原始 ACI 绝对阈值判断
    - 动态 ACI 滚动均值判断
    - LPR 双轨制验证
    """
    
    def __init__(self):
        # 配置参数
        self.aci_absolute_threshold = 24  # 月
        self.aci_rolling_window = 60  # 5年滚动窗口
        self.lpr_ma_window = 6  # 6个月移动平均
        self.fpi_threshold = 0  # 资金链盈亏平衡点
        
    def calculate_aci_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 ACI 相关指标
        
        包含两种判断方式：
        1. 绝对阈值判断：ACI < 24个月
        2. 动态阈值判断：ACI < 近5年滚动均值 且 ACI < 24个月
        
        Returns:
            添加列：
            - aci_5yr_ma: 过去5年滚动均值
            - I_ACI_absolute: 绝对阈值信号 (0/1)
            - I_ACI_dynamic: 动态阈值信号 (0/1)
            - I_ACI: 最终ACI信号 (优化后的动态判断)
        """
        
        result = df.copy()
        
        # 计算滚动5年均值
        result['aci_5yr_ma'] = result['aci_extended' if 'aci_extended' in result.columns else 'aci'].rolling(
            window=self.aci_rolling_window, 
            min_periods=12  # 至少1年数据
        ).mean()
        
        # 绝对阈值判断 (原有逻辑)
        base_col = 'aci_extended' if 'aci_extended' in result.columns else 'aci'
        result['I_ACI_absolute'] = (result[base_col] < self.aci_absolute_threshold).astype(int)
        
        # 动态阈值判断 (优化后)
        # 条件1: ACI < 过去5年均值 (去化周期低于历史平均)
        # 条件2: ACI < 24个月 (绝对安全线)
        result['I_ACI_dynamic'] = (
            (result[base_col] < result['aci_5yr_ma']) & 
            (result[base_col] < self.aci_absolute_threshold)
        ).astype(int)
        
        # 使用动态阈值作为最终判断
        result['I_ACI'] = result['I_ACI_dynamic']
        
        print(f"✅ ACI指标计算完成")
        print(f"   绝对阈值信号触发: {result['I_ACI_absolute'].sum()} 次")
        print(f"   动态阈值信号触发: {result['I_ACI_dynamic'].sum()} 次")
        
        return result
    
    def calculate_fpi_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 FPI (资金链压力) 指标
        
        I_FPI: 资金链压力信号
        - 值为正 = 房企净融资流入 (安全)
        - 值为负 = 房企净融资流出 (危险)
        
        Returns:
            添加列：
            - I_FPI: 资金链信号 (1=安全, 0=危险)
        """
        
        result = df.copy()
        
        fpi_col = 'net_financing_cash_flow'
        
        if fpi_col not in result.columns:
            print("⚠️ FPI数据不存在，跳过计算")
            result['I_FPI'] = 0
            return result
        
        # 原始FPI值
        result['FPI_raw'] = result[fpi_col]
        
        # 判断：净融资 > 0 为安全
        result['I_FPI'] = (result[fpi_col] > self.fpi_threshold).astype(int)
        
        # 资金压力等级
        result['FPI_stress_level'] = pd.cut(
            result[fpi_col],
            bins=[-np.inf, -5000, -2000, 0, 2000, np.inf],
            labels=[5, 4, 3, 2, 1]  # 5=极度危险, 1=非常安全
        ).astype(int)
        
        print(f"✅ FPI指标计算完成")
        print(f"   资金链安全信号: {result['I_FPI'].sum()} 次")
        
        return result
    
    def calculate_lpr_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 LPR (土地溢价率) 指标 - 双轨制验证
        
        原始逻辑：只看土地溢价率是否回升
        优化逻辑：
        - 条件1: 土地溢价率 MA6 回升 (短期趋势)
        - 条件2: 土地成交均价斜率 > 0 (价格真的在涨)
        
        Returns:
            添加列：
            - lpr_6ma: 土地溢价率6个月均值
            - lpr_slope: 土地溢价率斜率
            - land_price_slope: 土地成交均价斜率
            - I_LPR: 双轨制信号 (1=满足双条件, 0=不满足)
        """
        
        result = df.copy()
        
        # 土地溢价率列
        premium_col = 'premium_rate'
        
        if premium_col not in result.columns:
            print("⚠️ LPR数据不存在，跳过计算")
            result['I_LPR'] = 0
            return result
        
        # 计算6个月移动平均
        result['lpr_6ma'] = result[premium_col].rolling(window=self.lpr_ma_window, min_periods=3).mean()
        
        # 计算溢价率变化 (与上月相比)
        result['lpr_change'] = result[premium_col].diff()
        
        # 计算溢价率斜率 (过去6个月趋势)
        result['lpr_slope'] = result['premium_rate'].rolling(window=6, min_periods=3).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
            raw=True
        )
        
        # 计算土地成交均价 (如果有数据)
        if 'land_price' in result.columns:
            result['land_price_slope'] = result['land_price'].rolling(window=6, min_periods=3).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
                raw=True
            )
        else:
            # 模拟数据：假设与溢价率同向
            result['land_price_slope'] = result['lpr_slope'] * 0.5
        
        # 双轨制判断
        # 条件1: 溢价率回升 (斜率 > 0 或 当前值 > 均值)
        condition1 = (result['lpr_slope'] > 0) | (result[premium_col] > result['lpr_6ma'])
        
        # 条件2: 土地均价真的在涨 (斜率 > 0)
        condition2 = result['land_price_slope'] > 0
        
        # 最终信号：同时满足双条件
        result['I_LPR'] = (condition1 & condition2).astype(int)
        
        print(f"✅ LPR双轨制指标计算完成")
        print(f"   溢价率回升信号: {((result['lpr_slope'] > 0) | (result[premium_col] > result['lpr_6ma'])).sum()} 次")
        print(f"   均价上涨信号: {(result['land_price_slope'] > 0).sum()} 次")
        print(f"   双轨制同时满足: {result['I_LPR'].sum()} 次")
        
        return result
    
    def calculate_ci_composite(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 CI 复合指标
        
        CI = ACI × 0.4 + FPI × 0.3 + LPR × 0.3
        
        Returns:
            添加列：
            - CI: 复合指标 (0-1)
            - CI_signal: 综合研判信号
        """
        
        result = df.copy()
        
        # 确保各指标列存在
        for col in ['I_ACI', 'I_FPI', 'I_LPR']:
            if col not in result.columns:
                result[col] = 0
        
        # 复合指标计算
        result['CI'] = (
            result['I_ACI'] * 0.4 + 
            result['I_FPI'] * 0.3 + 
            result['I_LPR'] * 0.3
        )
        
        # 综合研判信号
        # CI > 0.7: 强烈买入信号
        # CI < 0.3: 强烈卖出信号
        result['CI_signal'] = pd.cut(
            result['CI'],
            bins=[-np.inf, 0.3, 0.5, 0.7, np.inf],
            labels=['强烈卖出', '观望', '谨慎买入', '强烈买入']
        )
        
        print(f"✅ CI复合指标计算完成")
        print(f"   强烈买入信号: {(result['CI'] > 0.7).sum()} 次")
        print(f"   强烈卖出信号: {(result['CI'] < 0.3).sum()} 次")
        
        return result
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有指标
        """
        print("=" * 50)
        print("开始计算所有指标...")
        print("=" * 50)
        
        # ACI 指标
        df = self.calculate_aci_indicators(df)
        
        # FPI 指标
        df = self.calculate_fpi_indicators(df)
        
        # LPR 双轨制指标
        df = self.calculate_lpr_indicators(df)
        
        # CI 复合指标
        df = self.calculate_ci_composite(df)
        
        print("=" * 50)
        print("指标计算完成!")
        print("=" * 50)
        
        return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    对外接口：计算所有指标
    """
    calculator = IndicatorCalculator()
    return calculator.calculate_all(df)


if __name__ == "__main__":
    # 测试
    dates = pd.date_range(start="2015-01-01", end="2024-12-01", freq='ME')
    n = len(dates)
    
    test_df = pd.DataFrame({
        'date': dates,
        'aci': np.random.uniform(12, 48, n),
        'aci_extended': np.random.uniform(18, 60, n),
        'net_financing_cash_flow': np.random.uniform(-5000, 8000, n),
        'premium_rate': np.random.uniform(0, 40, n),
    })
    
    result = calculate_indicators(test_df)
    print(result.tail(10))
