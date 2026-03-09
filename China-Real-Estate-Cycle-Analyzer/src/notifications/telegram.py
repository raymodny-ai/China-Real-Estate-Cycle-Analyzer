"""
Telegram Notification Module
发送报告到 Telegram
"""

from typing import Optional
import os


class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初始化通知器
        
        Args:
            bot_token: Telegram Bot Token
            chat_id: 目标聊天 ID
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """
        发送文本消息
        
        Args:
            text: 消息内容
            parse_mode: 解析模式 (Markdown/HTML)
            
        Returns:
            是否发送成功
        """
        if not self.bot_token or not self.chat_id:
            print(f"[Mock] Telegram message: {text[:100]}...")
            return True
            
        import requests
        
        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            return response.ok
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False
    
    def send_document(self, document: bytes, filename: str = "report.pdf", caption: str = "") -> bool:
        """
        发送文件
        
        Args:
            document: 文件字节数据
            filename: 文件名
            caption: 说明文字
            
        Returns:
            是否发送成功
        """
        if not self.bot_token or not self.chat_id:
            print(f"[Mock] Sending document: {filename}")
            return True
            
        import requests
        
        url = f"{self.api_url}/sendDocument"
        files = {'document': (filename, document)}
        data = {
            'chat_id': self.chat_id,
            'caption': caption
        }
        
        try:
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.ok
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False
    
    def send_report(self, city: str, indicators: dict, analysis: str, pdf_data: Optional[bytes] = None) -> bool:
        """
        发送完整报告
        
        Args:
            city: 城市名
            indicators: 指标数据
            analysis: 分析结果
            pdf_data: PDF 数据 (可选)
            
        Returns:
            是否发送成功
        """
        # 构建消息
        message = f"📊 *房地产周期分析报告*\n\n"
        message += f"🏙️ 城市: {city}\n\n"
        message += f"*核心指标:*\n"
        message += f"• ACI: {indicators.get('aci', 0):.1f} 个月\n"
        message += f"• FPI: {indicators.get('fpi', 0):,.0f}\n"
        message += f"• LPR: {indicators.get('lpr_5y', 0):.2f}%\n"
        message += f"• CI: {indicators.get('CI', 0):.2f}\n"
        
        # 发送文本
        success = self.send_message(message)
        
        # 发送 PDF
        if pdf_data and success:
            success = self.send_document(
                pdf_data, 
                filename=f"report_{city}.pdf",
                caption=f"{city} 详细分析报告"
            )
        
        return success


def send_alert(city: str, indicators: dict, analysis: str = "") -> bool:
    """
    便捷函数：发送告警
    
    Args:
        city: 城市
        indicators: 指标
        analysis: 分析
        
    Returns:
        是否成功
    """
    notifier = TelegramNotifier()
    return notifier.send_report(city, indicators, analysis)


if __name__ == "__main__":
    # 测试
    notifier = TelegramNotifier()
    
    test_indicators = {
        'aci': 18.5,
        'fpi': 5000,
        'lpr_5y': 4.2,
        'CI': 0.35
    }
    
    test_analysis = "测试分析报告"
    
    result = notifier.send_report("北京", test_indicators, test_analysis)
    print(f"Send result: {result}")
