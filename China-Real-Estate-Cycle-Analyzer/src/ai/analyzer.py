"""
AI Analysis Module
使用模拟 LLM 分析房地产周期指标
"""

from typing import Dict, Any, Optional
import random


class AIAnalyzer:
    """AI 分析器 - 用于解释指标含义"""
    
    def __init__(self, model: str = "mock"):
        """
        初始化分析器
        
        Args:
            model: 使用的模型 (mock/ deepseek)
        """
        self.model = model
        
    def analyze(self, indicators: Dict[str, Any], api_key: str = None) -> str:
        """
        分析指标并返回中文解释
        
        Args:
            indicators: 包含 ACI, FPI, LPR, CI 的字典
            api_key: DeepSeek API Key
            
        Returns:
            中文分析报告
        """
        if self.model == "mock":
            return self._mock_analyze(indicators)
        else:
            return self._deepseek_analyze(indicators, api_key)
    
    def _mock_analyze(self, indicators: Dict[str, Any]) -> str:
        """模拟分析 - 用于测试"""
        
        aci = indicators.get('aci', 0)
        fpi = indicators.get('fpi', 0)
        lpr = indicators.get('lpr_5y', 0)
        ci = indicators.get('CI', 0)
        
        # ACI 分析
        if aci < 12:
            aci_comment = "去化周期较短，市场活跃度高"
        elif aci < 24:
            aci_comment = "去化周期适中，市场平稳"
        else:
            aci_comment = "去化周期较长，库存压力较大"
        
        # FPI 分析
        if fpi > 0:
            fpi_comment = "资金链充裕，房企融资环境良好"
        else:
            fpi_comment = "资金链紧张，房企面临融资压力"
        
        # LPR 分析
        if lpr < 4.0:
            lpr_comment = "利率处于较低水平，购房成本降低"
        elif lpr < 4.5:
            lpr_comment = "利率适中"
        else:
            lpr_comment = "利率较高，购房成本增加"
        
        # CI 综合判断
        if ci > 0.5:
            ci_comment = "🏢 周期上行期，市场信心充足"
        elif ci > 0:
            ci_comment = "📊 周期温和回升"
        else:
            ci_comment = "📉 周期下行期，市场观望情绪浓厚"
        
        report = f"""
## 📊 房地产周期分析报告

### 1. ACI (去化周期) - {aci:.1f} 个月
{aci_comment}
- 警戒线: 24个月
- 当前状态: {'🟢 正常' if aci < 24 else '🔴 警戒'}

### 2. FPI (资金链) - {fpi:,.0f}
{fpi_comment}
- 临界值: 0
- 当前状态: {'🟢 安全' if fpi > 0 else '🔴 紧张'}

### 3. LPR (5年期) - {lpr:.2f}%
{lpr_comment}

### 4. 复合指数 (CI) - {ci:.2f}
{ci_comment}

### 💡 综合建议
{self._generate_suggestion(aci, fpi, lpr, ci)}

---
*报告由 AI 自动生成*
"""
        return report
    
    def _generate_suggestion(self, aci: float, fpi: float, lpr: float, ci: float) -> str:
        """生成综合建议"""
        
        suggestions = []
        
        if aci > 24:
            suggestions.append("• 库存较高，建议加快去化")
        if fpi < 0:
            suggestions.append("• 关注房企资金链风险")
        if lpr > 4.5:
            suggestions.append("• 融资成本较高，关注政策变化")
        if ci < 0:
            suggestions.append("• 市场处于下行周期，谨慎投资")
        
        if not suggestions:
            suggestions.append("• 市场运行平稳，保持关注")
        
        return "\n".join(suggestions)
    
    def _deepseek_analyze(self, indicators: Dict[str, Any], api_key: str = None) -> str:
        """
        DeepSeek API 分析
        
        Args:
            indicators: 指标数据
            api_key: DeepSeek API Key
            
        Returns:
            AI 分析报告
        """
        import os
        import requests
        
        api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        
        if not api_key:
            return self._mock_analyze(indicators)
        
        # 准备提示词
        aci = indicators.get('aci', 0)
        fpi = indicators.get('fpi', 0)
        lpr = indicators.get('lpr_5y', 0)
        ci = indicators.get('CI', 0)
        
        prompt = f"""请分析以下中国房地产周期指标，并用中文给出专业分析和建议：

1. ACI (去化周期): {aci:.1f} 个月 - 警戒线24个月
2. FPI (资金链): {fpi:,.0f} - 临界值0
3. LPR (5年期): {lpr:.2f}%
4. CI (复合指数): {ci:.2f}

请从以下几个方面分析：
- 当前市场状态判断
- 风险预警
- 投资建议
- 政策影响

请用 Markdown 格式输出。"""

        try:
            # 调用 DeepSeek API
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.ok:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                # API 调用失败，回退到模拟
                print(f"DeepSeek API error: {response.text}")
                return self._mock_analyze(indicators)
                
        except Exception as e:
            print(f"DeepSeek API exception: {e}")
            return self._mock_analyze(indicators)


def analyze_market(city: str = "北京", data: Optional[Dict] = None, api_key: str = None, use_mock: bool = True) -> str:
    """
    便捷函数：分析市场数据
    
    Args:
        city: 城市名称
        data: 指标数据字典
        api_key: DeepSeek API Key
        use_mock: 是否使用模拟模式
        
    Returns:
        分析报告字符串
    """
    if data is None:
        # 使用模拟数据
        data = {
            'aci': random.uniform(10, 30),
            'fpi': random.uniform(-10000, 10000),
            'lpr_5y': random.uniform(3.8, 4.8),
            'CI': random.uniform(-0.5, 0.5)
        }
    
    analyzer = AIAnalyzer(model="deepseek" if not use_mock else "mock")
    return analyzer.analyze(data, api_key)


if __name__ == "__main__":
    # 测试
    result = analyze_market()
    print(result)
