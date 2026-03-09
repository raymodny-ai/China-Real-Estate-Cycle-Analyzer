# China Real Estate Cycle Analyzer - 项目说明文档

> 项目地址: https://github.com/raymodny-ai/China-Real-Estate-Cycle-Analyzer

---

## 📋 项目简介

中国房地产周期分析器是一个基于 Streamlit 的可视化分析工具，用于监测和分析中国房地产市场的周期性变化。

### 核心功能

- **ACI (去化周期)** 分析
- **FPI (资金链压力)** 监测
- **LPR (贷款市场报价利率)** 追踪
- **复合指数 (CI)** 计算

---

## 🏗️ 项目架构

```
China-Real-Estate-Cycle-Analyzer/
├── app.py                 # Streamlit 仪表盘
├── config.py              # 配置加载器
├── config/
│   └── settings.yaml      # 参数配置文件
├── src/
│   ├── data_fetchers/     # 数据获取模块
│   │   ├── base.py
│   │   ├── nbs.py         # 国家统计局
│   │   └── eastmoney.py   # 东方财富
│   ├── models/            # 指标计算
│   │   ├── indicators.py
│   │   ├── policy_damping.py
│   │   └── predict_engine.py
│   └── utils/             # 工具模块
│       └── logging_config.py
├── tests/                 # 单元测试
├── docs/                  # 文档
├── logs/                  # 日志目录
├── data/                  # 数据目录
├── requirements.txt        # 依赖清单
└── pytest.ini             # pytest 配置
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd China-Real-Estate-Cycle-Analyzer
pip install -r requirements.txt
```

### 2. 启动仪表盘

```bash
streamlit run app.py
```

### 3. 访问

浏览器打开: http://localhost:8501

---

## ⚙️ 配置说明

编辑 `config/settings.yaml`:

```yaml
model:
  weights:
    aci: 0.4    # 去化周期权重
    fpi: 0.3    # 资金链权重
    lpr: 0.3    # 土地溢价率权重
  thresholds:
    aci_limit: 24        # ACI 警戒线 (月)
    fpi_threshold: 0   # FPI 临界值
```

---

## 📊 数据源

| 数据源 | 说明 | 状态 |
|--------|------|------|
| 国家统计局 (NBS) | ACI、去化周期 | 框架已就绪 |
| 东方财富 (East Money) | LPR 利率数据 | ✅ 可用 |

---

## 🧪 运行测试

```bash
pytest tests/ -v
```

---

## 📝 积分规则

| 行为 | 分数 |
|------|------|
| 成功接单 | +10 |
| 完成任务 | +50 |
| 错误/失败 | -20 |

---

*最后更新: 2026-03-09*
