"""
檢查當前小時的廣播狀態
"""

import os
import time
from datetime import datetime
from google.cloud import firestore
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def check_current_hour():
    """檢查當前小時的狀態"""
    db = firestore.Client()
    
    current_hour = int(time.time()) // 3600  # 486136 for 00:00
    current_time = datetime.now()
    
    print(f"=== 當前小時檢查 ===")
    print(f"當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"當前小時數: {current_hour}")
    print(f"對應時間: {datetime.fromtimestamp(current_hour * 3600).strftime('%Y-%m-%d %H:00')}")
    print("")
    
    # 檢查當前小時的訊息
    messages_ref = db.collection('broadcasts').document(str(current_hour))
    messages_doc = messages_ref.get()
    
    if messages_doc.exists:
        data = messages_doc.to_dict()
        message_count = data.get('message_count', 0)
        print(f"訊息數量: {message_count}")
        
        # 列出前幾則訊息
        if message_count > 0:
            print("\n最近的訊息:")
            messages = messages_ref.collection('messages').limit(5).stream()
            for msg in messages:
                msg_data = msg.to_dict()
                print(f"  - {msg_data.get('content', 'N/A')}")
                print(f"    時間: {msg_data.get('timestamp', 'N/A')}")
    else:
        print("❌ 沒有訊息文檔")
    
    print("\n=== 檢查廣播 ===")
    # 檢查是否有生成的廣播
    broadcast_ref = db.collection('generated_broadcasts').document(str(current_hour))
    broadcast_doc = broadcast_ref.get()
    
    if broadcast_doc.exists:
        broadcast_data = broadcast_doc.to_dict()
        print(f"✅ 有廣播")
        print(f"生成時間: {broadcast_data.get('generated_at', 'N/A')}")
        print(f"訊息數: {broadcast_data.get('message_count', 0)}")
        print(f"內容: {broadcast_data.get('content', '')[:200]}...")
    else:
        print("❌ 沒有廣播")
        
    # 檢查最新的廣播
    print("\n=== 最新廣播 (最近24小時) ===")
    twenty_four_hours_ago = (current_hour - 24) * 3600
    
    latest_broadcasts = db.collection('generated_broadcasts')\
        .where('timestamp', '>=', twenty_four_hours_ago)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(3)\
        .stream()
    
    for broadcast in latest_broadcasts:
        data = broadcast.to_dict()
        hour = data.get('hour', 0)
        timestamp = data.get('timestamp', 0)
        broadcast_time = datetime.fromtimestamp(timestamp)
        print(f"\n小時 {hour} ({broadcast_time.strftime('%Y-%m-%d %H:00')})")
        print(f"  訊息數: {data.get('message_count', 0)}")
        print(f"  內容: {data.get('content', '')[:100]}...")

if __name__ == "__main__":
    check_current_hour()