"""
檢查廣播執行狀況
"""

import os
import time
import requests
from datetime import datetime, timedelta
from google.cloud import firestore
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def check_broadcast_execution():
    """檢查廣播執行狀況"""
    db = firestore.Client()
    
    current_time = datetime.now()
    current_hour = int(time.time()) // 3600
    
    print(f"=== 廣播執行狀況檢查 ===")
    print(f"當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"當前小時: {current_hour}")
    print("")
    
    # 檢查最近 5 小時的廣播
    print("=== 最近 5 小時的廣播狀態 ===")
    for i in range(5):
        check_hour = current_hour - i
        hour_time = datetime.fromtimestamp(check_hour * 3600)
        
        # 檢查訊息
        messages_doc = db.collection('broadcasts').document(str(check_hour)).get()
        message_count = 0
        if messages_doc.exists:
            message_count = messages_doc.to_dict().get('message_count', 0)
        
        # 檢查廣播
        broadcast_doc = db.collection('generated_broadcasts').document(str(check_hour)).get()
        
        status = ""
        if broadcast_doc.exists:
            broadcast_data = broadcast_doc.to_dict()
            generated_at = broadcast_data.get('generated_at', 'N/A')
            if isinstance(generated_at, datetime):
                generated_at = generated_at.strftime('%H:%M:%S')
            status = f"✅ 有廣播 (生成於 {generated_at})"
        elif message_count > 0:
            status = f"❌ 有 {message_count} 則訊息但沒有廣播"
        else:
            status = "⚪ 沒有訊息"
        
        print(f"{hour_time.strftime('%Y-%m-%d %H:00')} - {status}")
    
    print("\n=== 測試廣播生成端點 ===")
    try:
        response = requests.post('https://frequency-bot-808270083585.asia-east1.run.app/generate-broadcast', timeout=10)
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.json()}")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    
    # 檢查最新廣播內容
    print("\n=== 最新廣播內容 ===")
    latest_broadcast = db.collection('generated_broadcasts')\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(1)\
        .stream()
    
    for broadcast in latest_broadcast:
        data = broadcast.to_dict()
        timestamp = data.get('timestamp', 0)
        broadcast_time = datetime.fromtimestamp(timestamp)
        print(f"時間: {broadcast_time.strftime('%Y-%m-%d %H:00')}")
        print(f"訊息數: {data.get('message_count', 0)}")
        print(f"內容預覽: {data.get('content', '')[:200]}...")

if __name__ == "__main__":
    check_broadcast_execution()