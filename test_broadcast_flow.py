"""
測試廣播流程
"""

import os
import time
import requests
from datetime import datetime
from frequency_bot_firestore import FrequencyBotFirestore
from knowledge_graph import KnowledgeGraph
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def test_broadcast_flow():
    """測試完整的廣播流程"""
    # 初始化
    try:
        knowledge_graph = KnowledgeGraph()
        print("✅ 知識圖譜連接成功")
    except:
        knowledge_graph = None
        print("⚠️  知識圖譜未連接")
    
    frequency_bot = FrequencyBotFirestore(knowledge_graph)
    
    print("\n=== 測試廣播流程 ===")
    
    # 1. 添加測試訊息
    print("\n1. 添加測試訊息到廣播池")
    message_count = frequency_bot.add_to_broadcast(
        message="這是一條測試訊息，用來驗證廣播系統是否正常運作。時間：" + datetime.now().strftime("%H:%M:%S"),
        user_id="test_user_123"
    )
    print(f"   ✅ 訊息已添加，當前訊息數: {message_count}")
    
    # 2. 檢查統計
    print("\n2. 檢查頻率統計")
    stats = frequency_bot.get_frequency_stats()
    print(f"   訊息數: {stats['message_count']}")
    print(f"   進度: {stats['progress_percent']}%")
    print(f"   距離下次廣播: {stats['time_until_broadcast']['minutes']}分{stats['time_until_broadcast']['seconds']}秒")
    
    # 3. 生成廣播
    print("\n3. 生成廣播")
    broadcast_data = frequency_bot.generate_hourly_broadcast()
    
    if broadcast_data:
        print(f"   ✅ 廣播生成成功")
        print(f"   小時: {broadcast_data.get('hour')}")
        print(f"   訊息數: {broadcast_data.get('message_count')}")
        print(f"   優化類型: {broadcast_data.get('optimization_type')}")
        print(f"   內容預覽: {broadcast_data.get('content', '')[:100]}...")
    else:
        print(f"   ❌ 沒有生成廣播")
    
    # 4. 獲取最新廣播
    print("\n4. 獲取最新廣播")
    latest = frequency_bot.get_latest_broadcast()
    if latest:
        timestamp = datetime.fromtimestamp(latest['timestamp'])
        print(f"   ✅ 最新廣播時間: {timestamp.strftime('%Y-%m-%d %H:00')}")
        print(f"   內容預覽: {latest.get('content', '')[:100]}...")
    else:
        print(f"   ❌ 沒有找到廣播")
    
    # 5. 測試 API 端點
    print("\n5. 測試 /generate-broadcast 端點")
    try:
        response = requests.post('https://frequency-bot-808270083585.asia-east1.run.app/generate-broadcast', timeout=10)
        print(f"   狀態碼: {response.status_code}")
        print(f"   回應: {response.json()}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")

if __name__ == "__main__":
    test_broadcast_flow()