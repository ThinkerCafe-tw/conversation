#!/usr/bin/env python3
"""
測試 webhook 接龍功能
"""

import requests
import json
import time

# 測試資料
test_messages = [
    "接龍 蘋果",      # 開始接龍
    "接龍狀態",       # 查看狀態
    "果汁",           # 繼續接龍（應該被識別為接龍）
    "汁液",           # 繼續接龍
    "錯誤",           # 測試錯誤（不符合接龍規則）
    "液體"            # 繼續接龍
]

# 模擬 LINE webhook 請求
def send_webhook_request(message):
    url = "http://localhost:8080/webhook"
    
    # 模擬 LINE webhook 資料格式
    data = {
        "destination": "test_destination",
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": f"test_{int(time.time() * 1000)}",
                    "text": message
                },
                "timestamp": int(time.time() * 1000),
                "source": {
                    "type": "user",
                    "userId": "test_user_123"
                },
                "replyToken": f"test_reply_token_{int(time.time() * 1000)}"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Line-Signature": "test_signature"  # 在開發環境中應該會被忽略
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"發送: {message}")
        print(f"回應: {response.status_code}")
        print("-" * 50)
        time.sleep(1)  # 避免過快發送
    except Exception as e:
        print(f"錯誤: {e}")

# 測試健康檢查
def test_health():
    url = "http://localhost:8080/health"
    try:
        response = requests.get(url)
        print("健康檢查:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        print("-" * 50)
    except Exception as e:
        print(f"健康檢查錯誤: {e}")

# 主程式
if __name__ == "__main__":
    print("=== 測試 Webhook 接龍功能 ===\n")
    
    # 先檢查健康狀態
    test_health()
    
    # 測試每個訊息
    for msg in test_messages:
        send_webhook_request(msg)
    
    print("\n測試完成！")