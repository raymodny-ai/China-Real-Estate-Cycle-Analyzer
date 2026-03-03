"""
政策干预阻尼模块

针对"中共稳房价策略"节点：
- 检测行政干预因素
- 引入政策干预阻尼系数 (Discount Factor)
- 当非市场化因素导致价格跌幅与资金压力不匹配时，延后底部确认时间
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime


class PolicyDampingAnalyzer:
    """
    政策干预阻尼分析器
    
    功能：
    1. 识别政策干预信号
    2. 计算阻尼系数
    3. 延后底部时间预测
    """
    
    # 政策干预类型
    POLICY_TYPES = {
        'price_limit': {
            'name': '限跌令',
            'damping': 1.3,  # 30% 延后
            'description': '地方政府出台限跌令'
        },
        'mortgage_rationing': {
            'name': '房贷松绑',
            'damping': 0.9,  # 略微提前
            'description': '降低首付比例/放宽限购'
        },
        'subsidy': {
            'name': '购房补贴',
            'damping': 0.85,
            'description': '财政补贴购房'
        },
        'land_constraint': {
            'name': '土拍限制',
            'damping': 1.2,
            'description': '限制土地出让/设置底价'
        },
        'state_purchase': {
            'name': '国家队收储',
            'damping': 1.15,
            'description': '政府/国企收购商品房'
        },
        'interest_rate_cut': {
            'name': '降息',
            'damping': 0.95,
            'description': 'LPR降息'
        }
    }
    
    def __init__(self):
        self.current_damping = 1.0  # 默认无干预
        
    def detect_policy_intervention(
        self,
        fpi: float,
        price_decline_rate: float,
        date: datetime = None
    ) -> Dict:
        """
        检测政策干预信号
        
        原理：
        - 正常市场：FPI < 0 (资金链紧张) → 价格跌幅大
        - 政策干预：FPI < 0 但 价格跌幅小 → 说明有托底
        
        Args:
            fpi: 资金链压力指数
            price_decline_rate: 价格跌幅
            date: 日期
        
        Returns:
            检测结果
        """
        
        # 正常情况下的预期跌幅 (基于FPI)
        # FPI = -3000 时，正常跌幅应该在 15%以上
        if fpi < -3000:
            expected_decline_min = 0.15
        elif fpi < -1000:
            expected_decline_min = 0.08
        else:
            expected_decline_min = 0.03
            
        # 实际跌幅与预期对比
        gap = expected_decline_min - price_decline_rate
        
        # 判断是否有政策干预
        if gap > 0.05:
            # 实际跌幅远低于预期，可能有托底政策
            intervention = True
            confidence = 'high' if gap > 0.10 else 'medium'
            intervention_type = 'price_floor'  # 限跌类
        elif gap < -0.05:
            # 实际跌幅超预期，市场出清中
            intervention = False
            confidence = 'high'
            intervention_type = 'market_clearing'
        else:
            intervention = False
            confidence = 'low'
            intervention_type = 'normal'
        
        return {
            'date': date,
            'fpi': fpi,
            'price_decline': price_decline_rate,
            'expected_decline': expected_decline_min,
            'gap': gap,
            'intervention': intervention,
            'intervention_type': intervention_type,
            'confidence': confidence
        }
    
    def calculate_damping_coefficient(
        self,
        interventions: List[Dict],
        market_health: float = None
    ) -> float:
        """
        计算综合阻尼系数
        
        Args:
            interventions: 检测到的干预信号列表
            market_health: 市场健康度 (0-1, 越低越可能干预)
        
        Returns:
            阻尼系数 (>1 延后底部, <1 提前底部)
        """
        
        if not interventions:
            return 1.0
            
        # 基础阻尼
        damping = 1.0
        
        # 干预信号加权
        intervention_count = sum(1 for i in interventions if i.get('intervention', False))
        
        if intervention_count > 0:
            # 每次干预增加 10-20% 延后
            damping += intervention_count * 0.15
            
        # 市场健康度影响
        if market_health is not None:
            if market_health < 0.3:
                damping += 0.2  # 越差越可能干预
            elif market_health < 0.5:
                damping += 0.1
                
        # 限制范围
        damping = min(max(damping, 0.8), 2.0)
        
        return damping
    
    def get_policy_events(self, start_year: int = 2020) -> pd.DataFrame:
        """
        获取历史政策事件时间线
        
        实际项目应接入真实政策数据
        
        Returns:
            DataFrame with columns: [date, policy_type, description, impact]
        """
        
        events = [
            # 2020年
            {'date': '2020-01-01', 'policy_type': 'mortgage_rationing', 'description': 'LPR改革启动', 'impact': 'neutral'},
            {'date': '2020-03-01', 'policy_type': 'subsidy', 'description': '多地出台购房补贴', 'impact': 'positive'},
            
            # 2021年
            {'date': '2021-01-01', 'policy_type': 'land_constraint', 'description': '土拍两集中政策', 'impact': 'negative'},
            {'date': '2021-09-01', 'policy_type': 'price_limit', 'description': '多地出台限跌令', 'impact': 'positive'},
            
            # 2022年
            {'date': '2022-03-01', 'policy_type': 'interest_rate_cut', 'description': 'LPR下调', 'impact': 'positive'},
            {'date': '2022-05-01', 'policy_type': 'subsidy', 'description': '购置税减免', 'impact': 'positive'},
            {'date': '2022-11-01', 'policy_type': 'state_purchase', 'description': '央行支持房贷', 'impact': 'positive'},
            {'date': '2022-12-01', 'policy_type': 'mortgage_rationing', 'description': '限购松绑', 'impact': 'positive'},
            
            # 2023年
            {'date': '2023-01-01', 'policy_type': 'interest_rate_cut', 'description': 'LPR继续下调', 'impact': 'positive'},
            {'date': '2023-08-01', 'policy_type': 'state_purchase', 'description': '认房不认贷', 'impact': 'positive'},
            {'date': '2023-10-01', 'policy_type': 'price_limit', 'description': '限跌令扩大', 'impact': 'positive'},
            
            # 2024年
            {'date': '2024-01-01', 'policy_type': 'interest_rate_cut', 'description': 'LPR大幅下调', 'impact': 'positive'},
            {'date': '2024-05-01', 'policy_type': 'state_purchase', 'description': '国家队收储商品房', 'impact': 'positive'},
            {'date': '2024-09-01', 'policy_type': 'mortgage_rationing', 'description': '一线城市松绑', 'impact': 'positive'},
        ]
        
        df = pd.DataFrame(events)
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['date'].dt.year >= start_year]
        
        return df
    
    def analyze_damping(
        self,
        price_data: pd.DataFrame,
        fpi_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        全面分析政策阻尼
        
        Args:
            price_data: 价格数据
            fpi_data: 资金链数据
        
        Returns:
            添加阻尼系数的DataFrame
        """
        
        # 合并数据
        df = price_data.copy()
        if 'date' in fpi_data.columns:
            df = df.merge(fpi_data[['date', 'net_financing_cash_flow']], on='date', how='left')
        
        # 初始化
        df['intervention_detected'] = False
        df['damping_factor'] = 1.0
        df['policy_signal'] = 'normal'
        
        # 政策事件
        policy_events = self.get_policy_events()
        
        # 检测每个时间点
        for i, row in df.iterrows():
            date = row.get('date')
            fpi = row.get('net_financing_cash_flow', 0)
            price_decline = row.get('decline_rate', 0)
            
            # 检测干预
            detection = self.detect_policy_intervention(fpi, price_decline, date)
            
            # 检查该时间点附近是否有政策事件
            if date is not None:
                nearby_events = policy_events[
                    (policy_events['date'] <= date) & 
                    (policy_events['date'] >= date - pd.Timedelta(days=90))
                ]
                
                if len(nearby_events) > 0:
                    detection['intervention'] = True
                    detection['policy_type'] = nearby_events.iloc[0]['policy_type']
            
            df.loc[i, 'intervention_detected'] = detection['intervention']
            df.loc[i, 'policy_signal'] = detection['intervention_type']
            
            # 基础阻尼
            damping = 1.0
            
            if detection['intervention']:
                # 获取政策类型的阻尼系数
                policy_type = detection.get('policy_type', 'price_limit')
                if policy_type in self.POLICY_TYPES:
                    damping = self.POLICY_TYPES[policy_type]['damping']
                else:
                    damping = 1.2  # 默认
                    
            df.loc[i, 'damping_factor'] = damping
        
        # 滚动平均阻尼
        df['damping_rolling'] = df['damping_factor'].rolling(6, min_periods=1).mean()
        
        return df
    
    def get_bottom_adjustment(
        self,
        base_months: float,
        damping_data: pd.DataFrame,
        current_date: datetime = None
    ) -> Dict:
        """
        获取底部时间调整
        
        Args:
            base_months: 基础预测月数
            damping_data: 阻尼数据
            current_date: 当前日期
        
        Returns:
            调整结果
        """
        
        if current_date is None:
            current_date = datetime.now()
            
        # 获取最近6个月的平均阻尼
        if 'damping_rolling' in damping_data.columns:
            recent = damping_data.tail(6)
            avg_damping = recent['damping_rolling'].mean()
        else:
            avg_damping = 1.0
            
        # 调整后的月数
        adjusted_months = base_months * avg_damping
        
        # 新的底部时间
        bottom_date = current_date + pd.Timedelta(days=30 * adjusted_months)
        
        # 判断状态
        if avg_damping > 1.3:
            status = '远离底部 (政策托底)'
            confidence = 'low'
        elif avg_damping > 1.1:
            status = '接近底部 (轻微干预)'
            confidence = 'medium'
        else:
            status = '市场底部 (自由出清)'
            confidence = 'high'
            
        return {
            'base_months': base_months,
            'avg_damping': avg_damping,
            'adjusted_months': adjusted_months,
            'bottom_date': bottom_date.strftime('%Y-%m'),
            'status': status,
            'confidence': confidence,
            'recommendation': '建议继续观察' if avg_damping > 1.2 else '可考虑入场'
        }


def analyze_policy_damping(
    price_data: pd.DataFrame,
    fpi_data: pd.DataFrame
) -> pd.DataFrame:
    """
    对外接口：分析政策阻尼
    """
    analyzer = PolicyDampingAnalyzer()
    return analyzer.analyze_damping(price_data, fpi_data)


if __name__ == "__main__":
    # 测试
    dates = pd.date_range(start="2021-01-01", end="2024-12-01", freq='ME')
    n = len(dates)
    
    price_df = pd.DataFrame({
        'date': dates,
        'decline_rate': np.random.uniform(0.01, 0.20, n),
    })
    
    fpi_df = pd.DataFrame({
        'date': dates,
        'net_financing_cash_flow': np.random.uniform(-5000, 2000, n),
    })
    
    result = analyze_policy_damping(price_df, fpi_df)
    
    print("\n政策阻尼分析结果:")
    print(result[['date', 'decline_rate', 'intervention_detected', 'damping_factor', 'policy_signal']].tail(12))
    
    # 测试底部调整
    analyzer = PolicyDampingAnalyzer()
    adjustment = analyzer.get_bottom_adjustment(24, result)
    print("\n底部时间调整:")
    print(adjustment)
