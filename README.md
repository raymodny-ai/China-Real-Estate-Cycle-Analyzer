# 中国房价底部预测模型 (CI Model)

本项目基于“库存去化与银行信用约束模型”，通过量化多维市场指标，构建动态面板来测算和追踪中国房地产市场的周期底部。

## 理论基础与核心指标
逻辑链条：`需求端萎缩 -> 库存堆高 -> 现金流紧张 -> 银行收缩 -> 土地流拍 -> 价格触底`

涵盖三大核心指标：
1. **去化周期 (ACI)**: 可售库存面积与销售面积比。底线阈值为2年（24个月）。
2. **房企资金链压力指数 (FPI)**: 核心房企净融资额度趋势。底线阈值为资金转正。
3. **土地溢价拍买率 (LPR)**: 土地市场热度及溢价情况。底线阈值为溢价止跌回暖。
综合以上三者计算出复合指标 (CI Index)。

## 安装指引
本项目需要 Python 3.x 版本。

1. **安装依赖**:
```bash
pip install -r requirements.txt
```

2. **数据初始化与获取**:
由于系统采用了多维度数据抓取（内置了模拟及真实代理数据作为结构骨架），请先运行以下命令初始化并生成最新指标和回测数据：
```bash
# 确保在项目根目录运行 (f:\Financial Project\中国房价底部的思路及导图)
set PYTHONPATH=.

python src/data_fetchers/run_all.py
python src/models/indicators.py
python src/models/backtest.py
```
*(注：执行完毕后将在 `data/` 目录下生成 `housing_data.db` SQLite数据库文件)*

3. **启动数据监控面板 (Dashboard)**:
```bash
streamlit run app.py
```
执行后会在您的默认浏览器打开交互式 Dashboard 面板，供您详细审阅各个周期的指标、回测模拟以及日本比对数据。
