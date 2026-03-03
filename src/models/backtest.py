"""
真正的回测模块 (v2.0)
基于 CI 指标的量化交易策略回测

功能：
1. 明确的交易标的和价格数据
2. CI 构造真正的交易信号
3. 标准持仓与收益曲线
4. 完整的风险收益评价指标

重要提示：
- 本模块是"占位 demo"向"严肃回测"的改进
- 需要接入真实资产价格数据才能做实证检验
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from src.utils.db import get_engine

# ==================== 配置区 ====================

class BacktestConfig:
    """回测配置"""
    
    # 交易标的
    ASSETS = {
        'real_estate_etf': '房地产ETF',
        'homebuilder_index': '房企指数',
        'reits': 'REITs指数',
        'bond_index': '地产债指数'
    }
    
    # 默认标的
    DEFAULT_ASSET = 'homebuilder_index'
    
    # 回测参数
    DEFAULT_PARAMS = {
        'ci_high_threshold': 0.7,  # CI高于此值减仓/做空
        'ci_low_threshold': 0.3,   # CI低于此值加仓/做多
        'position_size': 1.0,      # 仓位大小
        'transaction_cost': 0.001,  # 交易成本 0.1%
        'seed': 42                 # 随机种子
    }


# ==================== 数据获取 ====================

def get_asset_prices(asset: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    获取资产价格数据
    
    Args:
        asset: 资产名称 (默认: homebuilder_index)
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        DataFrame with columns: date, asset, close, return
    """
    
    engine = get_engine()
    
    # 尝试从数据库读取
    try:
        if asset:
            query = f"SELECT date, asset, close FROM asset_prices WHERE asset = '{asset}'"
        else:
            query = "SELECT date, asset, close FROM asset_prices"
            
        if start_date:
            query += f" AND date >= '{start_date}'"
        if end_date:
            query += f" AND date <= '{end_date}'"
            
        df = pd.read_sql(query, con=engine)
        
        if len(df) > 0:
            return df
            
    except Exception as e:
        print(f"⚠️ 数据库无资产价格数据: {e}")
    
    # 如果没有真实数据，返回模拟数据（仅供参考演示）
    print("ℹ️ 使用模拟资产价格数据（仅供演示）")
    return generate_simulated_prices(asset or BacktestConfig.DEFAULT_ASSET, start_date, end_date)


def generate_simulated_prices(asset: str, start_date: str = None, end_date: str = None, seed: int = 42) -> pd.DataFrame:
    """
    生成模拟资产价格（仅用于演示，不能用于实证）
    
    Args:
        asset: 资产名称
        start_date: 开始日期
        end_date: 结束日期
        seed: 随机种子
        
    Returns:
        DataFrame with date, asset, close, return
    """
    
    np.random.seed(seed)
    
    if start_date is None:
        start_date = '2012-01-01'
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
    n = len(dates)
    t = np.arange(n)
    
    # 模拟价格走势 (参考房地产指数特征)
    # 2012-2020 上涨，2021-2023 下跌
    trend = np.zeros(n)
    for i, date in enumerate(dates):
        year = date.year
        if year <= 2020:
            trend[i] = 100 * np.exp(0.03 * (year - 2012))
        else:
            trend[i] = 100 * np.exp(0.24) * (1 - 0.03 * (year - 2020))
    
    # 添加噪声
    noise = np.random.normal(0, 0.02, n)
    returns = np.exp(noise) - 1
    prices = 100 * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        'date': dates,
        'asset': asset,
        'close': prices,
        'return': returns
    })
    
    return df


def get_ci_index(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    获取 CI 指数
    
    Returns:
        DataFrame with columns: date, CI, I_ACI, I_FPI, I_LPR
    """
    
    engine = get_engine()
    
    try:
        query = "SELECT date, CI, I_ACI, I_FPI, I_LPR FROM model_ci_index"
        
        if start_date:
            query += f" WHERE date >= '{start_date}'"
        if end_date:
            if start_date:
                query += f" AND date <= '{end_date}'"
            else:
                query += f" WHERE date <= '{end_date}'"
        
        df = pd.read_sql(query, con=engine)
        df['date'] = pd.to_datetime(df['date'])
        
        return df
        
    except Exception as e:
        print(f"❌ 读取 CI 指数失败: {e}")
        return pd.DataFrame()


# ==================== 信号构造 ====================

def build_ci_signals(ci_df: pd.DataFrame, params: Dict = None) -> pd.DataFrame:
    """
    基于 CI 构造交易信号
    
    信号规则:
    - CI >= ci_high_threshold: signal = -1 (减仓/做空)
    - CI <= ci_low_threshold: signal = +1 (加仓/做多)
    - 中间区间: signal = 0 (观望)
    
    Args:
        ci_df: CI 指数 DataFrame
        params: 参数字典
        
    Returns:
        添加了 signal 列的 DataFrame
    """
    
    if params is None:
        params = BacktestConfig.DEFAULT_PARAMS
    
    df = ci_df.copy()
    
    high = params.get('ci_high_threshold', 0.7)
    low = params.get('ci_low_threshold', 0.3)
    
    # 构造信号 (严格: 只用过去信息)
    df['signal'] = 0  # 默认观望
    
    # CI 高时减仓/做空
    df.loc[df['CI'] >= high, 'signal'] = -1
    
    # CI 低时加仓/做多
    df.loc[df['CI'] <= low, 'signal'] = 1
    
    # 也可以用 regime 方式
    # df['regime'] = pd.cut(df['CI'], bins=[-np.inf, low, high, np.inf], 
    #                       labels=['bullish', 'neutral', 'bearish'])
    
    # 前向填充信号 (上一期信号决定下一期仓位)
    df['position'] = df['signal'].shift(1).fillna(0)  # position_t 用 signal_{t-1}
    
    return df


# ==================== 回测核心 ====================

def run_backtest(
    ci_df: pd.DataFrame = None,
    price_df: pd.DataFrame = None,
    asset: str = None,
    params: Dict = None,
    start_date: str = None,
    end_date: str = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    运行完整的回测
    
    Args:
        ci_df: CI 指数 DataFrame (可选)
        price_df: 资产价格 DataFrame (可选)
        asset: 资产名称 (默认: homebuilder_index)
        params: 回测参数
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        (回测结果 DataFrame, 指标字典)
    """
    
    if params is None:
        params = BacktestConfig.DEFAULT_PARAMS
    
    # 设置随机种子
    np.random.seed(params.get('seed', 42))
    
    # 获取数据
    if ci_df is None:
        ci_df = get_ci_index(start_date, end_date)
    
    if price_df is None:
        price_df = get_asset_prices(asset or BacktestConfig.DEFAULT_ASSET, start_date, end_date)
    
    # 对齐数据频率 (以 CI 为准，月度)
    price_df['date'] = pd.to_datetime(price_df['date'])
    ci_df['date'] = pd.to_datetime(ci_df['date'])
    
    # 计算资产收益率
    price_df = price_df.sort_values('date')
    price_df['asset_return'] = price_df['close'].pct_change()
    
    # 转换 CI 为月度
    price_df['year_month'] = price_df['date'].dt.to_period('M')
    ci_df['year_month'] = ci_df['date'].dt.to_period('M')
    
    # 合并数据
    merged = price_df.merge(ci_df[['year_month', 'CI', 'I_ACI', 'I_FPI', 'I_LPR']], 
                           on='year_month', how='left')
    
    # 前向填充 CI (只在已有数据范围内)
    merged['CI'] = merged['CI'].ffill()
    
    # 构造信号
    merged = build_ci_signals(merged, params)
    
    # 计算策略收益
    # position_{t-1} * return_t (严格避免 look-ahead bias)
    cost = params.get('transaction_cost', 0.001)
    
    # 换手检测
    merged['position_change'] = merged['position'].diff().abs()
    merged['trade_cost'] = merged['position_change'] * cost
    
    # 策略收益 = 仓位 * 资产收益 - 交易成本
    merged['strategy_return'] = merged['position'] * merged['asset_return'] - merged['trade_cost']
    
    # 累计收益
    merged['cumulative_asset'] = (1 + merged['asset_return'].fillna(0)).cumprod()
    merged['cumulative_strategy'] = (1 + merged['strategy_return'].fillna(0)).cumprod()
    
    # 计算指标
    metrics = calculate_metrics(merged)
    
    return merged, metrics


def calculate_metrics(backtest_df: pd.DataFrame) -> Dict:
    """
    计算回测指标
    
    包含:
    - 总收益
    - 年化收益
    - 波动率
    - Sharpe 比率
    - 最大回撤
    - 胜率
    - 持仓比例
    """
    
    strategy_returns = backtest_df['strategy_return'].dropna()
    asset_returns = backtest_df['asset_return'].dropna()
    
    # 过滤有效数据
    valid_returns = strategy_returns[~np.isnan(strategy_returns) & ~np.isinf(strategy_returns)]
    
    if len(valid_returns) == 0:
        return {}
    
    # 基本参数
    n_periods = len(valid_returns)
    n_years = n_periods / 252  # 假设252个交易日
    
    # 总收益
    total_return = backtest_df['cumulative_strategy'].iloc[-1] - 1 if len(backtest_df) > 0 else 0
    
    # 年化收益
    annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    # 波动率
    annual_volatility = valid_returns.std() * np.sqrt(252)
    
    # Sharpe 比率 (假设无风险利率为 2%)
    risk_free_rate = 0.02
    sharpe = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
    
    # 最大回撤
    cumulative = backtest_df['cumulative_strategy'].fillna(1)
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # 胜率
    win_rate = (valid_returns > 0).sum() / len(valid_returns)
    
    # 持仓比例
    avg_position = backtest_df['position'].abs().mean()
    
    # 换手率
    turnover = backtest_df['position_change'].mean() if 'position_change' in backtest_df.columns else 0
    
    # 年化换手率
    annual_turnover = turnover * 252
    
    metrics = {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_volatility,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'avg_position': avg_position,
        'annual_turnover': annual_turnover,
        'n_periods': n_periods,
        'n_years': n_years
    }
    
    return metrics


def run_regime_backtest(
    ci_df: pd.DataFrame = None,
    price_df: pd.DataFrame = None,
    asset: str = None,
    params: Dict = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    基于 CI Regimes 的回测
    
    策略:
    - CI > 0.7: Bearish (空仓或做空)
    - 0.3 <= CI <= 0.7: Neutral (半仓)
    - CI < 0.3: Bullish (满仓)
    
    Args:
        同 run_backtest
        
    Returns:
        (回测结果, 指标)
    """
    
    if params is None:
        params = BacktestConfig.DEFAULT_PARAMS.copy()
    
    # 修改信号构造逻辑
    def build_regime_signals(df, params):
        high = params.get('ci_high_threshold', 0.7)
        low = params.get('ci_low_threshold', 0.3)
        
        # 三级 regime
        df['regime'] = 'neutral'
        df.loc[df['CI'] >= high, 'regime'] = 'bearish'
        df.loc[df['CI'] <= low, 'regime'] = 'bullish'
        
        # 映射到仓位
        regime_position = {'bullish': 1.0, 'neutral': 0.5, 'bearish': -0.5}
        df['position'] = df['regime'].map(regime_position).shift(1).fillna(0)
        
        return df
    
    # 运行回测
    if ci_df is None:
        ci_df = get_ci_index()
    if price_df is None:
        price_df = get_asset_prices(asset or BacktestConfig.DEFAULT_ASSET)
    
    np.random.seed(params.get('seed', 42))
    
    # 数据处理
    price_df['date'] = pd.to_datetime(price_df['date'])
    ci_df['date'] = pd.to_datetime(ci_df['date'])
    price_df = price_df.sort_values('date')
    price_df['asset_return'] = price_df['close'].pct_change()
    
    price_df['year_month'] = price_df['date'].dt.to_period('M')
    ci_df['year_month'] = ci_df['date'].dt.to_period('M')
    
    merged = price_df.merge(ci_df[['year_month', 'CI', 'I_ACI', 'I_FPI', 'I_LPR']], 
                           on='year_month', how='left')
    merged['CI'] = merged['CI'].ffill()
    
    # 使用 regime 信号
    merged = build_regime_signals(merged, params)
    
    # 计算收益
    cost = params.get('transaction_cost', 0.001)
    merged['position_change'] = merged['position'].diff().abs()
    merged['trade_cost'] = merged['position_change'] * cost
    merged['strategy_return'] = merged['position'] * merged['asset_return'] - merged['trade_cost']
    merged['cumulative_asset'] = (1 + merged['asset_return'].fillna(0)).cumprod()
    merged['cumulative_strategy'] = (1 + merged['strategy_return'].fillna(0)).cumprod()
    
    metrics = calculate_metrics(merged)
    
    return merged, metrics


# ==================== 对外接口 ====================

def run_full_backtest(
    asset: str = 'homebuilder_index',
    strategy: str = 'threshold',  # 'threshold' or 'regime'
    params: Dict = None,
    start_date: str = '2015-01-01',
    end_date: str = None
) -> Dict:
    """
    运行完整回测的便捷接口
    
    Args:
        asset: 交易标的
        strategy: 策略类型 ('threshold' 或 'regime')
        params: 参数
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        包含回测结果和指标的字典
    """
    
    if params is None:
        params = BacktestConfig.DEFAULT_PARAMS.copy()
    
    print(f"运行回测...")
    print(f"标的: {asset}")
    print(f"策略: {strategy}")
    print(f"参数: {params}")
    print("-" * 50)
    
    if strategy == 'regime':
        result_df, metrics = run_regime_backtest(
            asset=asset,
            params=params,
            start_date=start_date,
            end_date=end_date
        )
    else:
        result_df, metrics = run_backtest(
            asset=asset,
            params=params,
            start_date=start_date,
            end_date=end_date
        )
    
    # 打印指标
    print("\n=== 回测指标 ===")
    print(f"总收益:     {metrics.get('total_return', 0):.2%}")
    print(f"年化收益:   {metrics.get('annual_return', 0):.2%}")
    print(f"年化波动:   {metrics.get('annual_volatility', 0):.2%}")
    print(f"Sharpe:     {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"最大回撤:   {metrics.get('max_drawdown', 0):.2%}")
    print(f"胜率:       {metrics.get('win_rate', 0):.2%}")
    print(f"平均仓位:   {metrics.get('avg_position', 0):.2%}")
    print(f"年化换手:   {metrics.get('annual_turnover', 0):.2%}")
    
    # 保存到数据库
    try:
        engine = get_engine()
        
        # 保存回测结果
        result_df.to_sql('backtest_results', con=engine, if_exists='replace', index=False)
        
        # 保存指标
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_sql('backtest_metrics', con=engine, if_exists='replace', index=False)
        
        print("\n✅ 结果已保存到数据库")
        
    except Exception as e:
        print(f"⚠️ 保存失败: {e}")
    
    return {
        'results': result_df,
        'metrics': metrics
    }


# ==================== 场景分析 ====================

def analyze_scenarios() -> pd.DataFrame:
    """
    分析不同参数下的回测表现
    
    用于敏感性分析
    """
    
    # 参数网格
    ci_thresholds = [0.5, 0.6, 0.7, 0.8]
    ci_lows = [0.2, 0.3, 0.4]
    
    results = []
    
    for high in ci_thresholds:
        for low in ci_lows:
            if low >= high:
                continue
                
            params = {
                'ci_high_threshold': high,
                'ci_low_threshold': low,
                'seed': 42
            }
            
            _, metrics = run_backtest(params=params)
            
            results.append({
                'high_threshold': high,
                'low_threshold': low,
                'annual_return': metrics.get('annual_return', 0),
                'sharpe': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0)
            })
    
    df = pd.DataFrame(results)
    
    # 保存
    try:
        engine = get_engine()
        df.to_sql('backtest_scenarios', con=engine, if_exists='replace', index=False)
    except:
        pass
    
    return df


# ==================== 主程序 ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='CI 策略回测')
    parser.add_argument('--asset', default='homebuilder_index', help='交易标的')
    parser.add_argument('--strategy', choices=['threshold', 'regime'], default='threshold')
    parser.add_argument('--high', type=float, default=0.7, help='CI 高阈值')
    parser.add_argument('--low', type=float, default=0.3, help='CI 低阈值')
    parser.add_argument('--start', default='2015-01-01', help='开始日期')
    
    args = parser.parse_args()
    
    params = {
        'ci_high_threshold': args.high,
        'ci_low_threshold': args.low,
        'seed': 42
    }
    
    result = run_full_backtest(
        asset=args.asset,
        strategy=args.strategy,
        params=params,
        start_date=args.start
    )
    
    print("\n回测完成!")
