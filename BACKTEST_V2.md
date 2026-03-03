# 回测模块 v2.0 说明文档

## 版本更新

本次更新将原来的"蒙特卡洛玩具模型"升级为"真正的量化回测框架"。

## 主要改进

### 1. 明确的交易标的
- 定义可交易资产：房地产ETF、房企指数、REITs、地产债指数
- 支持真实价格数据接入

### 2. 真正的交易信号
```python
# CI 阈值策略
CI >= 0.7 → signal = -1 (减仓/做空)
CI <= 0.3 → signal = +1 (加仓/做多)
中间区间  → signal = 0  (观望)
```

### 3. 严格避免 Look-ahead Bias
```python
# position_t 由 signal_{t-1} 决定
position = signal.shift(1).fillna(0)
```

### 4. 完整的风险收益指标
| 指标 | 说明 |
|------|------|
| total_return | 总收益 |
| annual_return | 年化收益 |
| annual_volatility | 年化波动率 |
| sharpe_ratio | Sharpe 比率 |
| max_drawdown | 最大回撤 |
| win_rate | 胜率 |
| avg_position | 平均仓位 |
| annual_turnover | 年化换手率 |

### 5. 可复现性
```python
np.random.seed(seed)  # 设置随机种子
```

## 使用方法

### 命令行运行
```bash
python src/models/backtest.py --asset homebuilder_index --high 0.7 --low 0.3
```

### Streamlit 展示
```bash
streamlit run app.py
```

## 策略类型

### 1. 阈值策略 (threshold)
- 简单阈值判断
- 适合初学者理解

### 2. Regime 策略 (regime)
- 三级 regime: bullish / neutral / bearish
- 仓位: 100% / 50% / -50%

## 数据要求

### 当前状态
- 资产价格: 使用模拟数据（演示用）
- 需要接入真实数据才能做实证检验

### 建议接入的数据源
1. 房地产ETF历史价格
2. 房企指数 (如中证房地产指数)
3. REITs 数据
4. 地产债收益率

## 注意事项

⚠️ **重要提示**:
- 当前回测基于模拟价格数据，仅供参考演示
- 需要接入真实资产价格才能做实证检验
- 回测结果不代表未来收益

## 文件结构

```
src/models/
├── indicators.py    # CI 指标计算
├── backtest.py      # 回测模块 v2.0
└── __init__.py
```

## 扩展建议

1. **多因子策略**: 加入宏观因子（利率、人口）
2. **机器学习**: 用 ML 模型预测 CI
3. **实盘对接**: 对接券商API实现自动化交易
