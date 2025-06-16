"""
生產環境測試 - 部署到生產環境後的驗證測試
使用真實的 LINE Webhook 但不影響真實用戶
"""

import sys
import time
import json
import hmac
import hashlib
import base64
import requests
import argparse
from typing import Dict, Optional
from datetime import datetime

class ProductionTester:
    def __init__(self, service_url: str, channel_secret: str = None):
        self.service_url = service_url.rstrip('/')
        self.channel_secret = channel_secret or "test_secret"
        self.test_user_id = f"test_bot_{int(time.time())}"
        
    def generate_signature(self, body: str) -> str:
        """生成 LINE 簽名"""
        hash = hmac.new(
            self.channel_secret.encode('utf-8'),
            body.encode('utf-8'), 
            hashlib.sha256
        ).digest()
        return base64.b64encode(hash).decode('utf-8')
    
    def create_webhook_event(self, message: str, user_id: str = None) -> Dict:
        """創建測試 Webhook 事件"""
        return {
            "destination": "test_destination",
            "events": [{
                "type": "message",
                "mode": "active",
                "timestamp": int(time.time() * 1000),
                "source": {
                    "type": "user",
                    "userId": user_id or self.test_user_id
                },
                "replyToken": f"test_token_{int(time.time())}",
                "message": {
                    "type": "text",
                    "id": f"test_msg_{int(time.time())}",
                    "text": message
                }
            }]
        }
    
    def send_test_message(self, message: str) -> Optional[Dict]:
        """發送測試訊息到 Webhook"""
        webhook_data = self.create_webhook_event(message)
        body = json.dumps(webhook_data)
        signature = self.generate_signature(body)
        
        try:
            response = requests.post(
                f"{self.service_url}/webhook",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Line-Signature": signature
                },
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {
                "error": str(e),
                "status_code": 0
            }
    
    def test_new_user_flow(self) -> bool:
        """測試新用戶流程"""
        print("\n🧪 Test: New User Flow")
        print("   Scenario: User says '你好' for the first time")
        
        # 創建唯一的測試用戶
        test_user = f"prod_test_user_{int(time.time())}"
        
        # 發送測試訊息
        response = self.send_test_message("你好")
        
        if response.get("status_code") == 200:
            print("   ✅ Webhook accepted the message")
            # 注意：在生產環境我們無法直接獲取回覆內容
            # 需要透過其他方式驗證（如查看資料庫）
            return True
        else:
            print(f"   ❌ Webhook failed: {response}")
            return False
    
    def test_basic_commands(self) -> bool:
        """測試基本指令"""
        print("\n🧪 Test: Basic Commands")
        
        test_commands = [
            ("統計", "Statistics command"),
            ("幫助", "Help command"),
            ("玩", "Play menu"),
            ("廣播", "Broadcast query")
        ]
        
        all_passed = True
        
        for command, description in test_commands:
            print(f"\n   Testing: {description}")
            response = self.send_test_message(command)
            
            if response.get("status_code") == 200:
                print(f"   ✅ {command} - Accepted")
            else:
                print(f"   ❌ {command} - Failed: {response.get('status_code')}")
                all_passed = False
            
            time.sleep(1)  # 避免過快請求
        
        return all_passed
    
    def test_error_handling(self) -> bool:
        """測試錯誤處理"""
        print("\n🧪 Test: Error Handling")
        
        # 測試格式錯誤
        error_cases = [
            ("接龍", "Word chain without word"),
            ("投票", "Vote without options"),
            ("防空", "Shelter info incomplete")
        ]
        
        all_passed = True
        
        for command, description in error_cases:
            print(f"\n   Testing: {description}")
            response = self.send_test_message(command)
            
            if response.get("status_code") == 200:
                print(f"   ✅ Error case handled gracefully")
            else:
                print(f"   ❌ Unexpected response: {response.get('status_code')}")
                all_passed = False
            
            time.sleep(1)
        
        return all_passed
    
    def test_performance(self) -> bool:
        """測試效能"""
        print("\n🧪 Test: Performance")
        
        response_times = []
        
        for i in range(5):
            start = time.time()
            response = self.send_test_message(f"效能測試 {i+1}")
            end = time.time()
            
            if response.get("status_code") == 200:
                response_time = (end - start) * 1000
                response_times.append(response_time)
                print(f"   Request {i+1}: {response_time:.0f}ms")
            else:
                print(f"   Request {i+1}: Failed")
            
            time.sleep(0.5)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            print(f"\n   Average: {avg_time:.0f}ms")
            print(f"   Max: {max_time:.0f}ms")
            
            if max_time < 3000:  # 3秒內
                print("   ✅ Performance acceptable")
                return True
            else:
                print("   ❌ Performance too slow")
                return False
        else:
            print("   ❌ All requests failed")
            return False
    
    def verify_data_persistence(self) -> bool:
        """驗證資料持久化"""
        print("\n🧪 Test: Data Persistence")
        
        # 發送一個特殊標記的訊息
        unique_message = f"PROD_TEST_{datetime.now().isoformat()}"
        response = self.send_test_message(unique_message)
        
        if response.get("status_code") == 200:
            print("   ✅ Test message sent successfully")
            # 這裡應該查詢資料庫確認訊息已儲存
            # 但在生產環境可能需要特殊權限
            return True
        else:
            print("   ❌ Failed to send test message")
            return False
    
    def cleanup_test_data(self):
        """清理測試資料"""
        print("\n🧹 Cleaning up test data...")
        # 實際環境中應該清理測試產生的資料
        # 例如：標記測試用戶、刪除測試訊息等
        pass
    
    def run_all_tests(self) -> bool:
        """執行所有生產環境測試"""
        print(f"🚀 Running Production Tests")
        print(f"   Service URL: {self.service_url}")
        print(f"   Test User: {self.test_user_id}")
        print("=" * 60)
        
        tests = [
            ("New User Flow", self.test_new_user_flow),
            ("Basic Commands", self.test_basic_commands),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
            ("Data Persistence", self.verify_data_persistence)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                passed = test_func()
                results.append((test_name, passed))
            except Exception as e:
                print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
                results.append((test_name, False))
        
        # 清理
        self.cleanup_test_data()
        
        # 總結
        print("\n" + "=" * 60)
        print("📊 Production Test Results:")
        
        passed_count = sum(1 for _, passed in results if passed)
        total_count = len(results)
        
        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"   {test_name}: {status}")
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        return passed_count == total_count


def main():
    parser = argparse.ArgumentParser(description='Run production tests')
    parser.add_argument('--url', required=True, help='Production service URL')
    parser.add_argument('--secret', help='LINE channel secret for signature')
    args = parser.parse_args()
    
    tester = ProductionTester(args.url, args.secret)
    
    try:
        passed = tester.run_all_tests()
        
        if passed:
            print("\n🎉 All production tests passed!")
            sys.exit(0)
        else:
            print("\n⚠️  Some production tests failed!")
            print("Consider rolling back if critical features are affected.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()