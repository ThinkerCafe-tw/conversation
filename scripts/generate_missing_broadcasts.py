"""
生成缺失的廣播
用於修復停留在 21:00 的問題
"""

import os
import time
import logging
from datetime import datetime, timedelta
from google.cloud import firestore
from frequency_bot_firestore import FrequencyBotFirestore
from knowledge_graph import KnowledgeGraph
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_missing_broadcasts():
    """找出有訊息但沒有生成廣播的小時"""
    db = firestore.Client()
    
    current_hour = int(time.time()) // 3600
    start_hour = current_hour - 24  # 檢查過去 24 小時
    
    missing_hours = []
    
    for hour in range(start_hour, current_hour + 1):
        # 檢查是否有訊息
        messages_ref = db.collection('broadcasts').document(str(hour))
        messages_doc = messages_ref.get()
        
        if messages_doc.exists:
            message_count = messages_doc.to_dict().get('message_count', 0)
            
            # 檢查是否有生成的廣播
            broadcast_ref = db.collection('generated_broadcasts').document(str(hour))
            broadcast_doc = broadcast_ref.get()
            
            if message_count > 0 and not broadcast_doc.exists:
                hour_time = datetime.fromtimestamp(hour * 3600)
                logger.info(f"發現缺失廣播 - 小時: {hour} ({hour_time.strftime('%Y-%m-%d %H:00')}), 訊息數: {message_count}")
                missing_hours.append(hour)
    
    return missing_hours

def generate_broadcasts_for_hours(hours):
    """為指定的小時生成廣播"""
    try:
        # 初始化知識圖譜
        knowledge_graph = KnowledgeGraph()
        logger.info("知識圖譜連接成功")
    except Exception as e:
        logger.warning(f"知識圖譜連接失敗: {e}")
        knowledge_graph = None
    
    # 初始化頻率機器人
    frequency_bot = FrequencyBotFirestore(knowledge_graph)
    
    for hour in hours:
        logger.info(f"正在生成小時 {hour} 的廣播...")
        
        # 臨時修改當前時間來生成過去的廣播
        original_time = time.time
        time.time = lambda: hour * 3600 + 1800  # 設定為該小時的中間時間
        
        try:
            broadcast_data = frequency_bot.generate_hourly_broadcast()
            if broadcast_data:
                logger.info(f"✅ 成功生成小時 {hour} 的廣播")
            else:
                logger.warning(f"⚠️ 小時 {hour} 沒有生成廣播（可能沒有訊息）")
        except Exception as e:
            logger.error(f"❌ 生成小時 {hour} 的廣播失敗: {e}")
        finally:
            # 恢復原始時間函數
            time.time = original_time
        
        # 避免 API 速率限制
        time.sleep(2)

def main():
    logger.info("=== 開始檢查缺失的廣播 ===")
    
    # 找出缺失的廣播
    missing_hours = find_missing_broadcasts()
    
    if not missing_hours:
        logger.info("✅ 沒有缺失的廣播")
        return
    
    logger.info(f"發現 {len(missing_hours)} 個缺失的廣播")
    
    # 詢問是否生成
    if input("是否要生成這些缺失的廣播？(y/n): ").lower() == 'y':
        generate_broadcasts_for_hours(missing_hours)
        logger.info("=== 完成 ===")
    else:
        logger.info("取消操作")

if __name__ == "__main__":
    main()