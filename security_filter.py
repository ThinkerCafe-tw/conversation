"""
安全過濾器：防止技術日誌和敏感資訊進入廣播系統
"""
import re
import logging

logger = logging.getLogger(__name__)

class SecurityFilter:
    """安全過濾器，防止敏感資訊洩漏"""
    
    def __init__(self):
        # 定義需要過濾的模式
        self.sensitive_patterns = [
            # 終端命令提示符
            (r'^\$\s*', 'SHELL_PROMPT'),
            (r'%\s*\w+', 'SHELL_COMMAND'),
            (r'^\(.*\)\s*\(.*\)\s*\w+@', 'TERMINAL_PROMPT'),
            
            # 日誌格式
            (r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+', 'TIMESTAMP_LOG'),
            (r'\|\s*(INFO|DEBUG|ERROR|WARNING)\s*\|', 'LOG_LEVEL'),
            
            # 檔案路徑和模組
            (r'[/\\]Users[/\\]\w+[/\\]', 'USER_PATH'),
            (r'\w+\.\w+:\w+:\d+', 'PYTHON_MODULE'),
            (r'line_pyautogui|pyautogui', 'AUTOMATION_TOOL'),
            
            # 技術指標
            (r'venv\)|virtualenv', 'VIRTUAL_ENV'),
            (r'line-cli|cli\s+\w+', 'CLI_COMMAND'),
            
            # IP 和連接埠
            (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'IP_ADDRESS'),
            (r':\d{4,5}\s', 'PORT_NUMBER'),
        ]
        
        # 定義替換規則
        self.replacements = {
            'SHELL_PROMPT': '',
            'SHELL_COMMAND': '',
            'TERMINAL_PROMPT': '',
            'TIMESTAMP_LOG': '[時間]',
            'LOG_LEVEL': '',
            'USER_PATH': '[路徑]',
            'PYTHON_MODULE': '[模組]',
            'AUTOMATION_TOOL': '[工具]',
            'VIRTUAL_ENV': '',
            'CLI_COMMAND': '[指令]',
            'IP_ADDRESS': '[IP]',
            'PORT_NUMBER': '[連接埠]',
        }
    
    def is_technical_content(self, text: str) -> bool:
        """檢測是否為技術內容"""
        technical_indicators = 0
        
        for pattern, _ in self.sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                technical_indicators += 1
        
        # 如果有3個以上技術指標，視為技術內容
        return technical_indicators >= 3
    
    def clean_message(self, text: str) -> str:
        """清理訊息中的敏感資訊"""
        if not text:
            return text
        
        cleaned_text = text
        detected_types = []
        
        # 檢測並替換敏感模式
        for pattern, pattern_type in self.sensitive_patterns:
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                detected_types.append(pattern_type)
                replacement = self.replacements.get(pattern_type, '')
                cleaned_text = re.sub(pattern, replacement, cleaned_text, flags=re.IGNORECASE)
        
        # 如果檢測到技術內容，記錄警告
        if detected_types:
            logger.warning(f"檢測到敏感內容類型: {detected_types}")
        
        # 移除多餘的空白
        cleaned_text = ' '.join(cleaned_text.split())
        
        return cleaned_text.strip()
    
    def validate_for_broadcast(self, text: str) -> tuple[bool, str]:
        """
        驗證訊息是否適合廣播
        返回: (是否通過, 清理後的訊息或錯誤提示)
        """
        # 檢查是否為技術內容
        if self.is_technical_content(text):
            logger.warning(f"拒絕技術內容: {text[:100]}...")
            return False, "🚫 偵測到技術日誌內容，請輸入一般對話訊息"
        
        # 清理訊息
        cleaned = self.clean_message(text)
        
        # 如果清理後內容太短，可能原本都是技術內容
        if len(cleaned) < 5 and len(text) > 50:
            return False, "🚫 訊息包含過多技術資訊，請重新輸入"
        
        return True, cleaned
    
    def get_security_stats(self) -> dict:
        """取得安全統計資料"""
        # 這裡可以實作統計功能
        return {
            'patterns_count': len(self.sensitive_patterns),
            'active': True
        }


# 使用範例
if __name__ == "__main__":
    filter = SecurityFilter()
    
    # 測試案例
    test_messages = [
        "venv) (base) sulaxd@sulaxddeMacBook-Pro LINE_pyautogui % line-cli open",
        "2025-06-16 12:47:33.079 | INFO | line_pyautogui.line_automation:is_line_running:29",
        "今天天氣真好",
        "我想玩遊戲",
        "/Users/sulaxd/Documents/project/test.py",
        "連接到 192.168.1.1:8080"
    ]
    
    for msg in test_messages:
        is_valid, result = filter.validate_for_broadcast(msg)
        print(f"\n原始: {msg}")
        print(f"通過: {is_valid}")
        print(f"結果: {result}")