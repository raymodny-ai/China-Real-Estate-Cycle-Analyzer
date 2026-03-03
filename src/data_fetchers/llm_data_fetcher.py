"""
LLM 大模型数据获取模块
基于在线大模型智能获取中国房地产数据

使用方式：
1. 安装依赖: pip install openai requests
2. 配置 API Key
3. 运行: python src/data_fetchers/llm_data_fetcher.py

推荐模型：MiniMax、OpenAI、Claude 等支持函数调用的大模型
"""
import json
import os
import re
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd
from src.utils.db import get_engine

# ==================== 配置区 ====================

class LLMConfig:
    """LLM 配置"""
    
    # 选择 LLM 提供商: 'minimax', 'openai', 'anthropic'
    PROVIDER = os.getenv("LLM_PROVIDER", "minimax")
    
    # API Keys
    MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # 模型名称
    MODEL = os.getenv("LLM_MODEL", "MiniMax-M2.5")
    
    # API 基础 URL
    MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"

# ==================== LLM 提示词模板 ====================

# ACI 提示词
ACI_PROMPT = """
你是资深数据工程师+地产研究员。我要做中国房地产指标数据集，请你只使用可免费访问的数据源（优先官方，其次研究机构公开报告/网页），不要使用需要付费订阅的数据库。

任务：针对 ACI 去化周期，给出：
1) 明确口径：字段定义、公式、单位、频率（月度/季度/年度）、覆盖范围（全国/城市/房企）。
2) 免费数据来源清单：每个来源必须给"可点击URL + 页面/表名 + 关键字段名/表头"。如果没有可验证URL，写"无法确认"，不要猜。
3) 获取方式：可复现步骤（手工下载路径或可爬取的HTML表格位置；如果有公开接口也要写请求参数样例）。
4) 交叉验证：至少2个来源或"官方+报告"对同一字段做一致性检查，指出可能差异。

输出格式：先给一个 JSON（sources/fields/formula/frequency/coverage/retrieval/validation），再给一段 Python 抓取/清洗伪代码。

ACI口径确认：ACI=库存面积/销售面积（存销比、去化周期），请按此公式给出数据来源。

重要：只输出 JSON 和代码，不要输出长篇解读。每条结论后面必须附 URL 证据。
"""

# FPI 提示词
FPI_PROMPT = """
我是资深数据工程师+地产研究员。我需要一个可复现的 FPI（Financial Pressure Index）资金链压力指标，底层变量至少包含"net_financing_cash_flow（融资活动产生的现金流量净额）"，频率为季度/年度，粒度为单房企（上市房企优先）。

请你先做两件事：
1) 明确 FPI 的计算方式：若市面上存在"房地产行业压力指数/资金压力指数"等不同构建方法，请只选择能用公开财报字段复现的一种，并写出公式（例如用融资净现金流，短债、现金等组合）。
2) 给出免费取数路径：逐一列出可直接下载财报/现金流量表的官方披露渠道（交易所公告/年报季报PDF），并说明如何从现金流量表中定位"融资活动产生的现金流量净额/Net cash flows from financing activities"等字段，最后合并成面板数据。

限制：不要引用需要付费的 Wind/同花顺iFinD 等；若你无法提供"可下载的披露URL模板 + 字段定位方法"，就标注不可自动化。

输出格式：先给 JSON（formula/sources/field_mapping/retrieval_steps），再给 Python 伪代码。
重要：每条结论后面必须附 URL 证据。
"""

# LPR 提示词
LPR_PROMPT = """
你是资深数据工程师+地产研究员。我需要 LPR（土地溢价率）=（成交价-起拍价）/起拍价，或等价的 成交价/起拍价-1，请确认采用百分比格式。

免费数据源：优先找"公开可下载的土地市场月报/周报"里直接给出的溢价率或成交总价、起拍总价（能反推）；并标注报告的来源引用。

输出格式：先给 JSON（sources/formula/retrieval_steps/file_format），再给 Python 伪代码。

重要：
- 只输出 JSON 和代码，不要长篇解读
- 每条结论后面必须附 URL 证据
- 明确标注"可免费获取"vs"需要付费"
"""

# 输出结构 Schema
OUTPUT_SCHEMA = {
    "metric": "ACI/FPI/LPR",
    "definition": {
        "formula": "",
        "unit": "",
        "frequency": "",
        "notes": ""
    },
    "free_sources": [
        {
            "name": "",
            "url": "",
            "table_or_section": "",
            "fields": ["", ""],
            "coverage": "",
            "update_lag": ""
        }
    ],
    "retrieval": [
        {
            "method": "download|scrape|manual",
            "steps": ["", ""],
            "file_format": "xls|csv|html|pdf"
        }
    ],
    "validation": [
        {
            "check": "",
            "expected_issue": "",
            "fallback": ""
        }
    ]
}


# ==================== LLM 客户端 ====================

class LLMClient:
    """LLM 客户端基类"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
    def chat(self, prompt: str, system_prompt: str = None) -> str:
        raise NotImplementedError


class MiniMaxClient(LLMClient):
    """MiniMax LLM 客户端"""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key, 
            LLMConfig.MINIMAX_BASE_URL, 
            LLMConfig.MODEL
        )
        
    def chat(self, prompt: str, system_prompt: str = None) -> str:
        """调用 MiniMax API"""
        
        if not self.api_key:
            print("⚠️ 未配置 MiniMax API Key")
            return ""
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # 低温度，更确定性的输出
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"❌ MiniMax API 错误: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"❌ MiniMax 请求失败: {e}")
            return ""


class OpenAIClient(LLMClient):
    """OpenAI LLM 客户端"""
    
    def __init__(self, api_key: str):
        super().__init__(
            api_key, 
            LLMConfig.OPENAI_BASE_URL, 
            "gpt-4"
        )
        
    def chat(self, prompt: str, system_prompt: str = None) -> str:
        """调用 OpenAI API"""
        
        if not self.api_key:
            print("⚠️ 未配置 OpenAI API Key")
            return ""
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"❌ OpenAI API 错误: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"❌ OpenAI 请求失败: {e}")
            return ""


# ==================== LLM 数据获取器 ====================

class LLMDataFetcher:
    """
    基于 LLM 的数据获取器
    通过大模型智能分析数据来源并获取数据
    """
    
    def __init__(self):
        self.provider = LLMConfig.PROVIDER
        
        if self.provider == "minimax":
            self.client = MiniMaxClient(LLMConfig.MINIMAX_API_KEY)
        elif self.provider == "openai":
            self.client = OpenAIClient(LLMConfig.OPENAI_API_KEY)
        else:
            self.client = None
            
        self.prompts = {
            "ACI": ACI_PROMPT,
            "FPI": FPI_PROMPT,
            "LPR": LPR_PROMPT
        }
        
    def fetch_data_source_info(self, metric: str) -> Dict:
        """
        获取特定指标的数据源信息
        
        Args:
            metric: 'ACI', 'FPI', 'LPR'
            
        Returns:
            包含数据源信息的字典
        """
        
        if metric not in self.prompts:
            raise ValueError(f"未知指标: {metric}")
            
        prompt = self.prompts[metric]
        
        print(f"🤖 正在调用 LLM 获取 {metric} 数据源信息...")
        
        response = self.client.chat(prompt)
        
        if not response:
            print(f"❌ LLM 调用失败")
            return {}
            
        # 解析 JSON
        try:
            # 尝试提取 JSON 部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                print(f"✅ 成功获取 {metric} 数据源信息")
                return data
            else:
                print(f"⚠️ 无法解析 JSON 响应")
                return {"raw_response": response}
                
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析错误: {e}")
            return {"raw_response": response}
            
    def fetch_all_metrics(self) -> Dict[str, Dict]:
        """
        获取所有指标的数据源信息
        """
        
        results = {}
        
        for metric in ["ACI", "FPI", "LPR"]:
            results[metric] = self.fetch_data_source_info(metric)
            
        return results
    
    def generate_collector_code(self, metric: str, source_info: Dict) -> str:
        """
        根据 LLM 返回的数据源信息生成采集代码
        
        Args:
            metric: 指标名称
            source_info: LLM 返回的数据源信息
            
        Returns:
            Python 采集代码
        """
        
        # 从 source_info 提取关键信息
        sources = source_info.get("free_sources", [])
        retrieval = source_info.get("retrieval", [])
        
        code_template = f'''
"""
{metric} 数据采集器
基于 LLM 智能分析生成

数据来源:
{json.dumps(sources, indent=2, ensure_ascii=False)}

获取方式:
{json.dumps(retrieval, indent=2, ensure_ascii=False)}
"""

import requests
import pandas as pd
from datetime import datetime

# TODO: 根据上述数据源信息实现采集逻辑
# 1. 确定数据源 URL
# 2. 实现下载/爬取逻辑
# 3. 数据清洗和存储

def fetch_{metric.lower()}_data():
    """获取 {metric} 数据"""
    
    # 示例代码框架
    # 具体实现需要根据 source_info 填写
    
    data = []
    
    # 来源: {sources[0].get('name', 'N/A') if sources else 'N/A'}
    # URL: {sources[0].get('url', 'N/A') if sources else 'N/A'}
    
    return data

if __name__ == "__main__":
    df = fetch_{metric.lower()}_data()
    print(f"获取到 {{len(df)}} 条数据")
'''
        
        return code_template


# ==================== 对外接口 ====================

def fetch_data_sources_with_llm(metric: str = None) -> Dict:
    """
    使用 LLM 获取数据源信息
    
    Args:
        metric: 'ACI', 'FPI', 'LPR', 或 None(获取所有)
        
    Returns:
        数据源信息字典
    """
    
    fetcher = LLMDataFetcher()
    
    if metric:
        return fetcher.fetch_data_source_info(metric)
    else:
        return fetcher.fetch_all_metrics()


def generate_collector(metric: str) -> str:
    """
    生成数据采集代码
    
    Args:
        metric: 'ACI', 'FPI', 'LPR'
        
    Returns:
        Python 代码
    """
    
    fetcher = LLMDataFetcher()
    source_info = fetcher.fetch_data_source_info(metric)
    return fetcher.generate_collector_code(metric, source_info)


# ==================== 使用示例 ====================

def example():
    """使用示例"""
    
    print("=" * 60)
    print("LLM 数据获取器示例")
    print("=" * 60)
    
    # 配置 API Key (建议使用环境变量)
    # export MINIMAX_API_KEY="your_key"
    # export OPENAI_API_KEY="your_key"
    
    # 获取单个指标
    print("\n[1] 获取 ACI 数据源信息...")
    aci_info = fetch_data_sources_with_llm("ACI")
    print(json.dumps(aci_info, indent=2, ensure_ascii=False))
    
    # 获取所有指标
    print("\n[2] 获取所有指标数据源信息...")
    all_info = fetch_data_sources_with_llm()
    for metric, info in all_info.items():
        print(f"\n--- {metric} ---")
        print(json.dumps(info, indent=2, ensure_ascii=False)[:500] + "...")
    
    # 生成采集代码
    print("\n[3] 生成 ACI 采集代码...")
    code = generate_collector("ACI")
    print(code[:1000] + "...")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM 数据获取器')
    parser.add_argument('--metric', choices=['ACI', 'FPI', 'LPR', 'all'], default='all')
    parser.add_argument('--generate-code', action='store_true', help='生成采集代码')
    
    args = parser.parse_args()
    
    if args.generate_code:
        # 生成代码模式
        for metric in ['ACI', 'FPI', 'LPR']:
            code = generate_collector(metric)
            filename = f"fetcher_{metric.lower()}.py"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"✅ 已生成 {filename}")
    else:
        # 获取数据源信息模式
        result = fetch_data_sources_with_llm(args.metric)
        print(json.dumps(result, indent=2, ensure_ascii=False))
