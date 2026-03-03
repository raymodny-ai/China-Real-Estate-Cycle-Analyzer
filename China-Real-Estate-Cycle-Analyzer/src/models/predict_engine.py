"""
房价弹性系数预测引擎

根据导图要求：
- 中国弹性系数: 1.05
- 房价预计下跌 80%，目前仅下跌 30%
- 剩余下跌空间 = 80% - 30% = 50%

影响因素：
- 老龄化率
- 居民部门杠杆率
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta


class PricePredictionEngine:
    """
    房价弹性系数预测引擎
    
    功能：
    1. 基于弹性系数测算价格跌幅空间
    2. 引入老龄化率、杠杆率作为降维惩罚
    3. 生成未来底价估算曲线
    """
    
    # 中国弹性系数 (导图给定的 1.05)
    CHINA_ELASTICITY_COEFFICIENT = 1.05
    
    # 目标跌幅 (导图: 80%)
    TARGET_DECLINE_RATE = 0.80
    
    def __init__(self):
        self.current_decline_rate = 0.30  # 目前下跌 30%
        
    def calculate_remaining_decline(
        self,
        current_decline: float = None,
        target_decline: float = None
    ) -> Dict[str, float]:
        """
        计算剩余下跌空间
        
        Returns:
            remaining: 剩余跌幅空间
            target_price: 目标底价 (当前价格的百分比)
            current_price_pct: 当前位置 (%)
        """
        
        if current_decline is None:
            current_decline = self.current_decline_rate
            
        if target_decline is None:
            target_decline = self.TARGET_DECLINE_RATE
            
        remaining = target_decline - current_decline
        
        return {
            'current_decline': current_decline,
            'target_decline': target_decline,
            'remaining_decline': remaining,
            'current_price_pct': (1 - current_decline) * 100,  # 当前价格是原价的%
            'target_price_pct': (1 - target_decline) * 100,     # 目标价格是原价的%
        }
    
    def get_macro_penalty_factors(self) -> Dict[str, float]:
        """
        获取宏观惩罚因子
        
        基于：
        - 老龄化率
        - 居民部门杠杆率
        
        Returns:
            penalty_factors: 惩罚因子字典
        """
        
        # 2024年数据 (模拟)
        # 老龄化率: ~15.4%
        aging_rate = 0.154
        
        # 居民部门杠杆率: ~62%
        leverage_rate = 0.62
        
        # 惩罚因子计算
        # 老龄化惩罚: 超过10%后加速
        aging_penalty = 1.0 + max(0, (aging_rate - 0.10) * 2)
        
        # 杠杆率惩罚: 超过50%后加速
        leverage_penalty = 1.0 + max(0, (leverage_rate - 0.50) * 1.5)
        
        # 综合惩罚因子
        combined_penalty = (aging_penalty + leverage_penalty) / 2
        
        return {
            'aging_rate': aging_rate,
            'leverage_rate': leverage_rate,
            'aging_penalty': aging_penalty,
            'leverage_penalty': leverage_penalty,
            'combined_penalty': combined_penalty,
            'data_year': 2024
        }
    
    def predict_price_curve(
        self,
        months_ahead: int = 36,
        current_price: float = 100,
        monthly_decline_rate: float = None,
        include_penalty: bool = True
    ) -> pd.DataFrame:
        """
        预测未来价格曲线
        
        Args:
            months_ahead: 预测月数
            current_price: 当前价格 (基准=100)
            monthly_decline_rate: 月均跌幅 (默认根据弹性系数计算)
            include_penalty: 是否包含宏观惩罚
        
        Returns:
            DataFrame with columns: [date, price, price_pct, decline_rate, phase]
        """
        
        # 默认月均跌幅
        if monthly_decline_rate is None:
            # 根据弹性系数和目标跌幅计算
            # 假设3年去化，则月均跌幅 ≈ 0.8 / 36 ≈ 2.2%
            monthly_decline_rate = self.TARGET_DECLINE_RATE / months_ahead
        
        # 获取惩罚因子
        penalty = self.get_macro_penalty_factors()
        penalty_factor = penalty['combined_penalty'] if include_penalty else 1.0
        
        # 生成日期
        start_date = datetime.now()
        dates = [start_date + timedelta(days=30 * i) for i in range(months_ahead + 1)]
        
        # 生成价格曲线
        prices = [current_price]
        price_pcts = [100.0]
        decline_rates = [0.0]
        
        for i in range(1, months_ahead + 1):
            # 月度跌幅 (受惩罚因子影响)
            monthly = monthly_decline_rate * penalty_factor
            
            # 跌幅加速效应 (越到底部越慢)
            acceleration = 1.0 - (i / months_ahead) * 0.3
            monthly_adjusted = monthly * acceleration
            
            new_price = prices[-1] * (1 - monthly_adjusted)
            new_decline = 1 - new_price / current_price
            
            prices.append(new_price)
            price_pcts.append(new_price / current_price * 100)
            decline_rates.append(new_decline)
        
        # 阶段标记
        phases = []
        for i, decline in enumerate(decline_rates):
            if decline < 0.15:
                phases.append('上半场')
            elif decline < 0.30:
                phases.append('中前期')
            elif decline < 0.50:
                phases.append('中后期')
            elif decline < 0.70:
                phases.append('下半场')
            else:
                phases.append('底部区域')
        
        df = pd.DataFrame({
            'date': dates,
            'month': range(len(dates)),
            'price': prices,
            'price_pct': price_pcts,
            'decline_rate': decline_rates,
            'phase': phases
        })
        
        return df
    
    def calculate_bottom_time(
        self,
        current_decline: float = None,
        target_decline: float = None,
        monthly_decline_rate: float = 0.02,
        policy_damping: float = 1.0
    ) -> Dict[str, any]:
        """
        计算底部到达时间
        
        Args:
            current_decline: 当前跌幅
            target_decline: 目标跌幅
            monthly_decline_rate: 月均跌幅
            policy_damping: 政策干预阻尼系数 (默认1.0, >1表示延后)
        
        Returns:
            底部时间预测
        """
        
        if current_decline is None:
            current_decline = self.current_decline_rate
        if target_decline is None:
            target_decline = self.TARGET_DECLINE_RATE
            
        remaining = target_decline - current_decline
        
        # 基础月数
        base_months = remaining / monthly_decline_rate
        
        # 政策阻尼 (延后底部确认时间)
        adjusted_months = base_months * policy_damping
        
        # 预测底部时间
        bottom_date = datetime.now() + timedelta(days=30 * adjusted_months)
        
        return {
            'current_decline': current_decline,
            'target_decline': target_decline,
            'remaining_decline': remaining,
            'monthly_rate': monthly_decline_rate,
            'policy_damping': policy_damping,
            'base_months_to_bottom': base_months,
            'adjusted_months_to_bottom': adjusted_months,
            'bottom_date': bottom_date.strftime('%Y-%m'),
            'bottom_date_full': bottom_date.strftime('%Y-%m-%d'),
            'confidence': '低' if policy_damping > 1.5 else ('中' if policy_damping > 1.2 else '高')
        }
    
    def generate_prediction_report(self) -> str:
        """
        生成预测报告
        """
        
        # 基本计算
        basic = self.calculate_remaining_decline()
        
        # 宏观因子
        macro = self.get_macro_penalty_factors()
        
        # 底部时间
        bottom = self.calculate_bottom_time()
        
        # 生成报告
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║            中国房价底部预测报告 (弹性系数法)                  ║
╠══════════════════════════════════════════════════════════════╣
║  📊 核心参数                                                 ║
║  ─────────────────────────────────────────────────────────── ║
║  弹性系数: {self.CHINA_ELASTICITY_COEFFICIENT}
║  目标跌幅: {self.TARGET_DECLINE_RATE*100:.0f}%                                    ║
║  当前跌幅: {basic['current_decline']*100:.0f}%                                     ║
║  剩余跌幅: {basic['remaining_decline']*100:.1f}%                                    ║
║                                                              ║
║  📈 宏观惩罚因子 ({macro['data_year']}年)                              ║
║  ─────────────────────────────────────────────────────────── ║
║  老龄化率: {macro['aging_rate']*100:.1f}% → 惩罚: {macro['aging_penalty']:.2f}x              ║
║  杠杆率: {macro['leverage_rate']*100:.0f}% → 惩罚: {macro['leverage_penalty']:.2f}x              ║
║  综合惩罚: {macro['combined_penalty']:.2f}x                                    ║
║                                                              ║
║  ⏰ 底部时间预测                                             ║
║  ─────────────────────────────────────────────────────────── ║
║  月均跌幅假设: {bottom['monthly_rate']*100:.1f}%                                      ║
║  政策阻尼: {bottom['policy_damping']:.1f}x                                          ║
║  预计底部: {bottom['bottom_date']} (约 {bottom['adjusted_months_to_bottom']:.0f}个月)                ║
║  置信度: {bottom['confidence']}                                                ║
║                                                              ║
║  💰 价格空间                                                 ║
║  ─────────────────────────────────────────────────────────── ║
║  当前价格: {basic['current_price_pct']:.0f}% (原价100%)                             ║
║  目标底价: {basic['target_price_pct']:.0f}% (原价100%)                              ║
║  剩余空间: -{basic['remaining_decline']*100:.0f}%                                        ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report


def predict_housing_bottom() -> pd.DataFrame:
    """
    对外接口：预测房价底部
    """
    engine = PricePredictionEngine()
    
    # 生成预测曲线
    curve = engine.predict_price_curve(months_ahead=48)
    
    print(engine.generate_prediction_report())
    
    return curve


if __name__ == "__main__":
    df = predict_housing_bottom()
    print("\n预测曲线 (前12个月):")
    print(df.head(12))
