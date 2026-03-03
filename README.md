# 🇨🇳 中国房价底部预测模型 (China Housing Market Cycle Analyzer)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.28+-red?style=flat-square" alt="Streamlit">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">
</p>

本项目基于「库存去化与银行信用约束模型」，通过量化 ACI（去化周期）、FPI（资金链压力）、LPR（土地溢价率）三大核心指标，构建动态面板来测算和追踪中国房地产市场的周期底部。

---

## 📋 项目概述

### 核心逻辑

```
需求端萎缩 → 库存堆高 → 现金流紧张 → 银行收缩 → 土地流拍 → 价格触底
```

### 三大核心指标

| 指标 | 名称 | 计算方式 | 阈值 |
|------|------|----------|------|
| **ACI** | 去化周期 | 库存面积 / 销售面积 | < 24个月 |
| **FPI** | 资金链压力 | 房企净融资现金流 | > 0 |
| **LPR** | 土地溢价率 | (成交价-起拍价)/起拍价 | 回升 |
| **CI** | 复合指标 | ACI×0.4 + FPI×0.3 + LPR×0.3 | 综合研判 |

---

## 🏗️ 项目架构

```
China-Real-Estate-Cycle-Analyzer/
├── app.py                          # Streamlit 可视化 Dashboard
├── DATA_SOURCES.md                  # 数据源说明文档
├── BACKTEST_V2.md                   # 回测模块说明
├── requirements.txt                 # Python 依赖
│
├── src/
│   ├── data_fetchers/              # 数据获取模块
│   │   ├── run_all.py              # 数据获取入口
│   │   ├── macro_data.py           # ACI 模拟数据
│   │   ├── financial_data.py        # FPI 模拟数据
│   │   ├── land_data.py            # LPR 模拟数据
│   │   ├── real_data_fetcher.py    # 真实数据获取 (AKShare)
│   │   ├── rent_price_ratio.py     # 租售比数据
│   │   └── llm_data_fetcher.py    # LLM 智能数据获取
│   │
│   ├── models/                     # 模型计算模块
│   │   ├── indicators.py           # CI 指标计算
│   │   └── backtest.py             # 回测模块 v2.0
│   │
│   └── utils/
│       └── db.py                   # 数据库工具
│
└── data/                           # 数据存储
    └── housing_data.db              # SQLite 数据库
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**主要依赖:**
- `streamlit` - Web 可视化
- `pandas` - 数据处理
- `numpy` - 数值计算
- `plotly` - 交互式图表
- `sqlalchemy` - 数据库
- `akshare` - 免费开源数据 (可选)

### 2. 数据初始化

```bash
# 方式一: 使用模拟数据 (默认)
python src/data_fetchers/run_all.py

# 方式二: 使用真实数据 (需安装 akshare)
pip install akshare
python src/data_fetchers/run_all.py --real

# 方式三: 获取租售比数据
python src/data_fetchers/run_all.py --rent
```

### 3. 启动 Dashboard

```bash
streamlit run app.py
```

启动后在浏览器打开 http://localhost:8501

---

## 📊 数据获取方式

### 方式对比

| 方式 | 命令 | 数据质量 | 适用场景 |
|------|------|----------|----------|
| 模拟数据 | `(默认)` | 演示用 | 开发测试 |
| AKShare | `--real` | 可用于研究 | 程序化获取 |
| 租售比 | `--rent` | 演示用 | 租房市场 |
| LLM智能 | `--llm` | 探索用 | 数据源调研 |

### 推荐: 安装 AKShare

```bash
pip install akshare
```

AKShare 是免费开源的中国金融数据库，提供国家统计局等官方数据接口。

---

## 📈 功能模块

### 1. 核心指标计算

- **ACI**: 去化周期 = 库存面积 / 销售面积
- **FPI**: 资金链压力指数
- **LPR**: 土地溢价率
- **CI**: 复合指标 (加权组合)

### 2. 可视化 Dashboard

5 个功能页面：
1. **判断口诀与现状** - 底部信号识别
2. **CI 复合指标** - 综合研判走势
3. **核心三大指标** - ACI/FPI/LPR 详情
4. **历史回测** - CI 策略回测分析
5. **中日对比** - 日本泡沫经验参考

### 3. 回测模块 v2.0

真正的量化回测框架：

```bash
python src/models/backtest.py --asset homebuilder_index --high 0.7 --low 0.3
```

**支持功能:**
- 阈值策略 / Regime 策略
- 信号构造与回测
- 风险收益指标 (Sharpe/MDD/胜率等)
- 敏感性分析

---

## 🤖 LLM 数据获取

通过大模型智能分析数据源：

```bash
# 获取数据源信息
python src/data_fetch --llm

# 生成采集代码
python src/dataers/run_all.py_fetchers/run_all.py --llm --generate-code
```

需要配置 API Key:
```bash
export MINIMAX_API_KEY="your_key"
```

---

## 📱 Streamlit Dashboard 预览

| 页面 | 说明 |
|------|------|
| 底部判断 | 三大条件是否满足 |
| CI 指标 | 复合指数走势 |
| 三大指标 | ACI/FPI/LPR 详情 |
| 历史回测 | 策略收益曲线 |
| 中日对比 | 日本泡沫参考 |

---

## 🔧 配置说明

### 数据库

默认使用 SQLite: `data/housing_data.db`

### 参数调整

修改 `src/models/backtest.py` 中的参数:

```python
params = {
    'ci_high_threshold': 0.7,  # CI 高阈值
    'ci_low_threshold': 0.3,   # CI 低阈值
    'position_size': 1.0,      # 仓位大小
    'transaction_cost': 0.001, # 交易成本
    'seed': 42                 # 随机种子
}
```

---

## ⚠️ 免责声明

- 本项目仅供学习研究参考，不构成投资建议
- 当前资产价格数据为模拟数据，需接入真实数据才能做实证检验
- 回测结果不代表未来收益

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

*中国房价底部预测模型 - 基于宏观因子的量化分析框架*
