"""
自動測試腳本 - 模擬 LINE Webhook 請求
"""
import requests
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime

class LineWebhookTester:
    def __init__(self, webhook_url, channel_secret):
        self.webhook_url = webhook_url
        self.channel_secret = channel_secret
        
    def create_signature(self, body):
        """建立 LINE 簽名"""
        hash = hmac.new(
            self.channel_secret.encode('utf-8'),
            body.encode('utf-8'), 
            hashlib.sha256
        ).digest()
        return base64.b64encode(hash).decode('utf-8')
    
    def send_message(self, text, user_id="test_user_001"):
        """模擬發送訊息"""
        event = {
            "type": "message",
            "timestamp": int(time.time() * 1000),
            "source": {
                "type": "user",
                "userId": user_id
            },
            "replyToken": "test_reply_token_" + str(int(time.time())),
            "message": {
                "type": "text",
                "id": "test_msg_" + str(int(time.time())),
                "text": text
            }
        }
        
        body = json.dumps({"events": [event]})
        signature = self.create_signature(body)
        
        headers = {
            "Content-Type": "application/json",
            "X-Line-Signature": signature
        }
        
        response = requests.post(self.webhook_url, data=body, headers=headers)
        return response
    
    def run_test_suite(self):
        """執行完整測試套件"""
        print("🧪 開始自動測試...")
        
        test_cases = [
            ("你好", "測試基本訊息"),
            ("統計", "測試統計功能"),
            ("廣播", "測試廣播查詢"),
            ("測試訊息" + str(int(time.time())), "測試唯一訊息"),
        ]
        
        results = []
        for text, description in test_cases:
            print(f"\n📝 {description}: 發送 '{text}'")
            try:
                response = self.send_message(text)
                status = "✅ 成功" if response.status_code == 200 else f"❌ 失敗 ({response.status_code})"
                results.append({
                    "test": description,
                    "status": status,
                    "response": response.text
                })
                print(f"   {status}")
            except Exception as e:
                print(f"   ❌ 錯誤: {e}")
                results.append({
                    "test": description,
                    "status": "❌ 錯誤",
                    "error": str(e)
                })
            
            time.sleep(1)  # 避免太快
        
        return results
    
    def continuous_test(self, interval=300):
        """持續測試（每5分鐘）"""
        print(f"🔄 開始持續測試，每 {interval} 秒執行一次")
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n--- {timestamp} ---")
            self.run_test_suite()
            time.sleep(interval)

if __name__ == "__main__":
    # 設定測試參數
    WEBHOOK_URL = "https://frequency-bot-808270083585.asia-east1.run.app/webhook"
    CHANNEL_SECRET = "YOUR_LINE_CHANNEL_SECRET"  # 需要替換為實際的 secret
    
    tester = LineWebhookTester(WEBHOOK_URL, CHANNEL_SECRET)
    
    # 執行單次測試
    tester.run_test_suite()
    
    # 如果要持續測試，取消下面的註解
    # tester.continuous_test(300)  # 每5分鐘測試一次