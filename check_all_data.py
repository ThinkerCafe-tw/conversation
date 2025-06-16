#!/usr/bin/env python3
"""
檢查所有 Firestore 資料
"""

import os
from dotenv import load_dotenv
from google.cloud import firestore
from frequency_bot_firestore import FrequencyBotFirestore, format_broadcast_message, format_stats_message
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def check_all_data():
    """檢查所有資料"""
    try:
        # 初始化
        db = firestore.Client()
        bot = FrequencyBotFirestore()
        
        # 1. 檢查所有 broadcasts 文件
        logger.info("=== 檢查 broadcasts 集合 ===")
        broadcasts = db.collection('broadcasts').order_by('hour', direction=firestore.Query.DESCENDING).limit(10).stream()
        total_messages = 0
        for doc in broadcasts:
            data = doc.to_dict()
            msg_count = data.get('message_count', 0)
            total_messages += msg_count
            logger.info(f"Hour {doc.id}: {msg_count} 則訊息, 更新於 {data.get('updated_at')}")
            
        logger.info(f"總共 {total_messages} 則訊息")
        
        # 2. 檢查所有 generated_broadcasts 文件
        logger.info("\n=== 檢查 generated_broadcasts 集合 ===")
        generated = db.collection('generated_broadcasts').order_by('hour', direction=firestore.Query.DESCENDING).limit(10).stream()
        count = 0
        for doc in generated:
            count += 1
            data = doc.to_dict()
            logger.info(f"\nHour {doc.id}:")
            logger.info(f"  訊息數: {data.get('message_count')}")
            logger.info(f"  優化類型: {data.get('optimization_type')}")
            logger.info(f"  內容: {data.get('content', '(無內容)')[:100]}...")
            
        logger.info(f"\n總共 {count} 個廣播")
        
        # 3. 測試統計功能
        logger.info("\n=== 測試統計功能 ===")
        stats = bot.get_frequency_stats()
        logger.info(format_stats_message(stats))
        
        # 4. 測試最新廣播
        logger.info("\n=== 測試最新廣播 ===")
        latest = bot.get_latest_broadcast()
        if latest:
            logger.info(format_broadcast_message(latest))
        else:
            logger.info("沒有最新廣播")
            
        # 5. 手動生成過去時段的廣播（如果還沒生成）
        logger.info("\n=== 檢查並生成遺漏的廣播 ===")
        hours_with_messages = [486120, 486121, 486122, 486123]
        for hour in hours_with_messages:
            # 檢查是否已生成
            existing = db.collection('generated_broadcasts').document(str(hour)).get()
            if not existing.exists:
                logger.info(f"Hour {hour} 沒有廣播，嘗試生成...")
                # 這裡需要更複雜的邏輯來生成過去的廣播
                # 暫時跳過
            else:
                logger.info(f"Hour {hour} 已有廣播")
                
    except Exception as e:
        logger.error(f"檢查失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_data()