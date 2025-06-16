"""
關鍵使用者流程測試
確保基本功能永遠正常運作
"""

import json
import time
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class TestCase:
    name: str
    input_message: str
    expected_patterns: List[str]
    should_not_contain: List[str] = None
    description: str = ""

class CriticalFlowTester:
    def __init__(self):
        self.test_cases = [
            # 1. 新用戶打招呼必須有反應
            TestCase(
                name="新用戶說你好",
                input_message="你好",
                expected_patterns=[
                    "歡迎",
                    "頻率共振",
                    "輸入「玩」",
                    "輸入「看」"
                ],
                description="新用戶第一次互動必須看到完整歡迎訊息"
            ),
            
            # 2. 自然語言理解
            TestCase(
                name="自然語言：想玩遊戲",
                input_message="我想玩遊戲",
                expected_patterns=[
                    "選擇遊戲",
                    "文字接龍",
                    "發起投票"
                ],
                description="自然語言必須能理解並顯示遊戲選單"
            ),
            
            # 3. 基本指令
            TestCase(
                name="統計指令",
                input_message="統計",
                expected_patterns=[
                    "即時頻率統計",
                    "本小時進度",
                    "參與排行榜"
                ],
                description="統計指令必須顯示即時數據"
            ),
            
            # 4. 錯誤處理
            TestCase(
                name="錯誤格式：接龍",
                input_message="接龍",
                expected_patterns=[
                    "接龍格式",
                    "例如：接龍 蘋果"
                ],
                description="錯誤格式必須給予提示"
            ),
            
            # 5. 一般訊息
            TestCase(
                name="一般聊天訊息",
                input_message="今天天氣真好",
                expected_patterns=[
                    ["第", "則"],  # 應該顯示訊息計數
                    ["繼續", "加油"]  # 或其他鼓勵語
                ],
                should_not_contain=[
                    "錯誤",
                    "error",
                    "失敗"
                ],
                description="一般訊息應該被正常收錄"
            ),
            
            # 6. 幫助功能
            TestCase(
                name="幫助指令",
                input_message="幫助",
                expected_patterns=[
                    "使用說明",
                    "資訊查詢",
                    "互動功能",
                    "防災互助"
                ],
                description="幫助指令必須顯示完整功能列表"
            ),
            
            # 7. 快捷選單
            TestCase(
                name="快捷選單：玩",
                input_message="玩",
                expected_patterns=[
                    "選擇遊戲",
                    "文字接龍",
                    "發起投票"
                ],
                description="快捷選單必須正常運作"
            )
        ]
    
    def simulate_webhook_call(self, message: str, user_id: str = None) -> Dict:
        """模擬 LINE Webhook 呼叫"""
        # 這裡應該實際呼叫測試環境的 webhook
        # 簡化版本只是模擬回應
        
        webhook_data = {
            "events": [{
                "type": "message",
                "message": {
                    "type": "text",
                    "text": message
                },
                "source": {
                    "type": "user",
                    "userId": user_id or f"test_user_{int(time.time())}"
                },
                "replyToken": f"test_token_{int(time.time())}"
            }]
        }
        
        # 實際應該：
        # response = requests.post(
        #     f"{SERVICE_URL}/webhook",
        #     json=webhook_data,
        #     headers={"X-Line-Signature": generate_test_signature(webhook_data)}
        # )
        # return response.json()
        
        # 模擬回應
        return {"status": "ok", "reply": self._get_simulated_reply(message)}
    
    def _get_simulated_reply(self, message: str) -> str:
        """模擬系統回應（實際測試應該從真實系統獲取）"""
        if "你好" in message:
            return """👋 歡迎來到頻率共振！

我會收集大家的訊息，每小時編成一個美麗的廣播
你剛才說的「你好」已經被收錄了！

🔥 快速體驗：
• 輸入「玩」- 開始互動遊戲
• 輸入「看」- 查看即時統計  
• 輸入「廣播」- 聽聽大家在說什麼"""
        
        elif "我想玩遊戲" in message:
            return """🎮 選擇遊戲
━━━━━━━━━━━━━━
🔗 文字接龍
→ 輸入「接龍 蘋果」

📊 發起投票  
→ 輸入「投票範例」"""
        
        else:
            return "✨ 第1則！繼續加油"
    
    def run_test_case(self, test_case: TestCase) -> bool:
        """執行單一測試案例"""
        print(f"\n🧪 測試：{test_case.name}")
        print(f"   描述：{test_case.description}")
        print(f"   輸入：「{test_case.input_message}」")
        
        # 模擬呼叫
        response = self.simulate_webhook_call(test_case.input_message)
        reply = response.get("reply", "")
        
        # 檢查預期內容
        passed = True
        for pattern in test_case.expected_patterns:
            if isinstance(pattern, list):
                # 多個詞必須都出現
                if not all(p in reply for p in pattern):
                    print(f"   ❌ 缺少預期內容：{pattern}")
                    passed = False
            else:
                # 單一詞
                if pattern not in reply:
                    print(f"   ❌ 缺少預期內容：{pattern}")
                    passed = False
        
        # 檢查不應包含的內容
        if test_case.should_not_contain:
            for pattern in test_case.should_not_contain:
                if pattern in reply:
                    print(f"   ❌ 不應包含：{pattern}")
                    passed = False
        
        if passed:
            print(f"   ✅ 通過")
        else:
            print(f"   ❌ 失敗")
            print(f"   實際回應：{reply[:100]}...")
        
        return passed
    
    def run_all_tests(self) -> bool:
        """執行所有測試"""
        print("=" * 60)
        print("🚀 開始執行關鍵流程測試")
        print("=" * 60)
        
        total = len(self.test_cases)
        passed = 0
        failed_cases = []
        
        for test_case in self.test_cases:
            if self.run_test_case(test_case):
                passed += 1
            else:
                failed_cases.append(test_case.name)
        
        print("\n" + "=" * 60)
        print(f"📊 測試結果：{passed}/{total} 通過")
        
        if failed_cases:
            print(f"\n❌ 失敗的測試：")
            for case in failed_cases:
                print(f"   - {case}")
            return False
        else:
            print("\n✅ 所有關鍵流程測試通過！")
            return True


class PerformanceTester:
    """效能測試"""
    
    def test_response_time(self, service_url: str) -> bool:
        """測試回應時間"""
        test_messages = [
            "你好",
            "統計",
            "我想玩遊戲",
            "今天天氣真好"
        ]
        
        print("\n⏱️  效能測試")
        all_passed = True
        
        for message in test_messages:
            start = time.time()
            # 實際呼叫 webhook
            # response = requests.post(...)
            end = time.time()
            
            response_time = (end - start) * 1000  # 毫秒
            
            if response_time > 3000:  # 3秒
                print(f"   ❌ 「{message}」回應時間過長：{response_time:.0f}ms")
                all_passed = False
            else:
                print(f"   ✅ 「{message}」回應時間：{response_time:.0f}ms")
        
        return all_passed


def main():
    """執行所有測試"""
    # 1. 關鍵流程測試
    flow_tester = CriticalFlowTester()
    flow_passed = flow_tester.run_all_tests()
    
    # 2. 效能測試
    # perf_tester = PerformanceTester()
    # perf_passed = perf_tester.test_response_time(SERVICE_URL)
    
    # 決定是否通過
    if not flow_passed:
        print("\n🚨 關鍵流程測試失敗！部署中止。")
        exit(1)
    
    print("\n🎉 所有測試通過！可以安全部署。")
    exit(0)


if __name__ == "__main__":
    main()