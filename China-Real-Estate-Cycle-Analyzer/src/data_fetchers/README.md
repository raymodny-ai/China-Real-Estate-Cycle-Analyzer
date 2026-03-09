# China Real Estate Cycle Analyzer - Data Fetchers
# This module provides interfaces to real data sources

## Data Sources

### 1. National Bureau of Statistics (China)
- API: https://data.stats.gov.cn/
- Data: ACI (去化周期), housing sales, inventory

### 2. CRIC (克尔瑞)
- Provider: cric-data
- Data: sales, inventory by city

### 3. East Money (东方财富)
- API: https://datacenter.eastmoney.com/
- Data: LPR, financial data

### 4. Wind Financial Terminal
- Provider: Wind
- Data: FPI, financing

## Usage

```python
from src.data_fetchers.nbs import NBSDataFetcher
from src.data_fetchers.eastmoney import EastMoneyFetcher

# Fetch ACI data
nbs = NBSDataFetcher()
aci_data = nbs.get_aci_data(city="北京", start_date="2020-01", end_date="2024-12")

# Fetch LPR data
em = EastMoneyFetcher()
lpr_data = em.get_lpr_data()
```

## API Keys Required

- NBS: Free registration at https://data.stats.gov.cn/
- East Money: Free tier available
- Wind: Commercial license required
