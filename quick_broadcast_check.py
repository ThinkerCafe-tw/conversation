"""
快速檢查廣播狀態
"""

import os
import time
from datetime import datetime
from google.cloud import firestore
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def quick_check():
    """快速檢查廣播狀態"""
    db = firestore.Client()
    
    current_hour = int(time.time()) // 3600
    print(f"當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"當前小時: {current_hour}\n")
    
    # 查看最新 10 則廣播
    print("=== 最新廣播 (按時間排序) ===")
    broadcasts = db.collection('generated_broadcasts')\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(10)\
        .stream()
    
    count = 0
    for broadcast in broadcasts:
        count += 1
        data = broadcast.to_dict()
        hour = data.get('hour', 0)
        timestamp = data.get('timestamp', 0)
        message_count = data.get('message_count', 0)
        generated_at = data.get('generated_at', 'N/A')
        
        broadcast_time = datetime.fromtimestamp(timestamp)
        
        # 計算時間差
        time_diff = current_hour - hour
        if time_diff < 24:
            time_str = f"{time_diff} 小時前"
        else:
            time_str = f"{time_diff // 24} 天前"
        
        print(f"\n{count}. {broadcast_time.strftime('%Y-%m-%d %H:00')} ({time_str})")
        print(f"   訊息數: {message_count}")
        
        if isinstance(generated_at, datetime):
            print(f"   生成時間: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 檢查對應的訊息是否存在
        messages_doc = db.collection('broadcasts').document(str(hour)).get()
        if messages_doc.exists:
            actual_count = messages_doc.to_dict().get('message_count', 0)
            if actual_count != message_count:
                print(f"   ⚠️  訊息數不符: 實際 {actual_count} vs 廣播 {message_count}")
    
    if count == 0:
        print("沒有找到任何廣播記錄")
    
    # 檢查有訊息但沒廣播的時段
    print(f"\n\n=== 檢查最近 24 小時缺失的廣播 ===")
    missing_count = 0
    for i in range(24):
        check_hour = current_hour - i
        
        messages_doc = db.collection('broadcasts').document(str(check_hour)).get()
        if messages_doc.exists:
            message_count = messages_doc.to_dict().get('message_count', 0)
            if message_count > 0:
                broadcast_doc = db.collection('generated_broadcasts').document(str(check_hour)).get()
                if not broadcast_doc.exists:
                    hour_time = datetime.fromtimestamp(check_hour * 3600)
                    print(f"❌ {hour_time.strftime('%Y-%m-%d %H:00')} - {message_count} 則訊息但沒有廣播")
                    missing_count += 1
    
    if missing_count == 0:
        print("✅ 沒有缺失的廣播")

if __name__ == "__main__":
    quick_check()