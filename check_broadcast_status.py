"""
檢查廣播狀態
"""

import os
import time
from datetime import datetime
from google.cloud import firestore
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def check_broadcasts():
    """檢查廣播狀態"""
    db = firestore.Client()
    
    current_hour = int(time.time()) // 3600
    current_time = datetime.now()
    
    print(f"=== 廣播狀態檢查 ===")
    print(f"當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"當前小時數: {current_hour}")
    print(f"")
    
    # 檢查最近的廣播
    print("=== 最近的廣播 ===")
    broadcasts = db.collection('generated_broadcasts')\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(5)\
        .stream()
    
    for broadcast in broadcasts:
        data = broadcast.to_dict()
        hour = data.get('hour', 0)
        timestamp = data.get('timestamp', 0)
        message_count = data.get('message_count', 0)
        broadcast_time = datetime.fromtimestamp(timestamp)
        
        print(f"小時: {hour} ({broadcast_time.strftime('%Y-%m-%d %H:00')})")
        print(f"  訊息數: {message_count}")
        print(f"  內容: {data.get('content', '')[:100]}...")
        print("")
    
    # 檢查有訊息但沒有廣播的小時
    print("=== 檢查缺失的廣播 ===")
    for i in range(5):
        check_hour = current_hour - i
        
        # 檢查訊息
        messages_doc = db.collection('broadcasts').document(str(check_hour)).get()
        broadcast_doc = db.collection('generated_broadcasts').document(str(check_hour)).get()
        
        hour_time = datetime.fromtimestamp(check_hour * 3600)
        
        if messages_doc.exists:
            message_count = messages_doc.to_dict().get('message_count', 0)
            if message_count > 0 and not broadcast_doc.exists:
                print(f"❌ 小時 {check_hour} ({hour_time.strftime('%Y-%m-%d %H:00')}) - {message_count} 則訊息，但沒有廣播")
            elif message_count > 0:
                print(f"✅ 小時 {check_hour} ({hour_time.strftime('%Y-%m-%d %H:00')}) - {message_count} 則訊息，有廣播")
        else:
            print(f"⚪ 小時 {check_hour} ({hour_time.strftime('%Y-%m-%d %H:00')}) - 沒有訊息")

if __name__ == "__main__":
    check_broadcasts()