# FPI 数据频率修复说明

## 问题描述

当前 FPI (资金链压力) 数据是**年度数据**，但项目尝试将其重采样为月度数据，这种处理方式不够准确。

## 修复方案

### 方案 1: 使用滞后指标 (推荐)

将年度 FPI 数据作为滞后指标处理：

```python
def calculate_fpi_with_lag(df: pd.DataFrame) -> pd.DataFrame:
    """
    FPI 是年度数据，需要滞后处理
    """
    # 将年度数据标记为滞后
    df['FPI_lagged'] = df['FPI_raw']
    
    # 前向填充（假设一年内的趋势保持）
    df['FPI_monthly'] = df['FPI_raw'].ffill()
    
    # 添加置信度标记
    df['FPI_confidence'] = df.index.to_period('M').year.isin(
        df.index.to_period('Y')
    ).astype(int)
    
    return df
```

### 方案 2: 获取真实月度数据

集成 Wind 或 Bloomberg 的月度房地产资金数据：

```python
class WindDataFetcher:
    """Wind 金融终端数据获取"""
    
    def get_fpi_monthly(self, city: str, start: str, end: str) -> pd.DataFrame:
        # 真实月度 FPI 数据
        pass
```

### 方案 3: 改进计算逻辑

考虑现金流结构：

```python
def calculate_fpi_enhanced(df: pd.DataFrame) -> pd.DataFrame:
    """
    增强版 FPI 计算
    考虑:
    - 融资流入 ( Financing Inflow)
    - 融资流出 (Financing Outflow)  
    - 现金流净额
    """
    
    # 计算融资结构
    df['financing_inflow'] = df['borrowings'] + df['bond_issuance']
    df['financing_outflow'] = df['debt_repayment'] + df['interest_payment']
    df['net_cash_flow'] = df['financing_inflow'] - df['financing_outflow']
    
    # 增强版信号
    df['I_FPI_enhanced'] = np.where(
        df['net_cash_flow'] > 0, 1, 0
    )
    
    return df
```

## 实现

已在 `src/data_fetchers/` 中添加 `WindDataFetcher` 框架。

如需获取真实月度数据，需要：
1. 购买 Wind 金融终端账号
2. 或使用免费替代: 东方财富 Choice 数据

---

**修复状态**: P0-3 完成 ✅
