#!/usr/bin/env python3
"""
監控廣播生成狀態
"""

import os
import time
import subprocess
from datetime import datetime, timedelta
from google.cloud import firestore
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def monitor_broadcasts():
    """持續監控廣播生成狀態"""
    db = firestore.Client()
    
    print("=== 廣播監控系統啟動 ===")
    print("按 Ctrl+C 結束監控")
    print("")
    
    last_check_hour = -1
    
    while True:
        try:
            current_time = datetime.now()
            current_hour = int(time.time()) // 3600
            
            # 每小時只檢查一次
            if current_hour != last_check_hour:
                last_check_hour = current_hour
                
                print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 檢查小時 {current_hour}")
                
                # 檢查當前小時的訊息
                messages_doc = db.collection('broadcasts').document(str(current_hour)).get()
                
                if messages_doc.exists:
                    message_count = messages_doc.to_dict().get('message_count', 0)
                    print(f"  📬 訊息數: {message_count}")
                    
                    # 檢查是否有廣播
                    broadcast_doc = db.collection('generated_broadcasts').document(str(current_hour)).get()
                    
                    if broadcast_doc.exists:
                        print(f"  ✅ 廣播已生成")
                    else:
                        if message_count > 0:
                            print(f"  ⚠️  有 {message_count} 則訊息但沒有廣播")
                            print(f"  🔄 等待 Cloud Scheduler 自動生成...")
                        else:
                            print(f"  ⚪ 沒有訊息，不需要廣播")
                else:
                    print(f"  ⚪ 本小時沒有活動")
                
                # 檢查 Cloud Scheduler 狀態
                print("\n  📅 Cloud Scheduler 狀態:")
                try:
                    result = subprocess.run(
                        ["gcloud", "scheduler", "jobs", "describe", "generate-hourly-broadcast", 
                         "--location=asia-east1", "--format=value(lastAttemptTime,state)"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        output = result.stdout.strip().split('\t')
                        if len(output) >= 2:
                            last_attempt = output[0] if output[0] else "尚未執行"
                            state = output[1] if len(output) > 1 else "未知"
                            print(f"     最後執行: {last_attempt}")
                            print(f"     狀態: {state}")
                except Exception as e:
                    print(f"     無法取得排程狀態: {e}")
            
            # 每分鐘更新一次狀態
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\n監控結束")
            break
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_broadcasts()