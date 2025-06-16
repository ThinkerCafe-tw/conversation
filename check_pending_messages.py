#!/usr/bin/env python3
"""
Check pending messages for current and recent hours
"""

import os
import sys
from dotenv import load_dotenv
from frequency_bot_firestore import FrequencyBotFirestore
from knowledge_graph import KnowledgeGraph
import logging
import time
from datetime import datetime

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def check_pending_messages():
    """Check pending messages"""
    try:
        # 初始化
        try:
            knowledge_graph = KnowledgeGraph()
            logger.info("知識圖譜連接成功")
        except Exception as e:
            logger.warning(f"知識圖譜連接失敗: {e}")
            knowledge_graph = None
            
        bot = FrequencyBotFirestore(knowledge_graph)
        logger.info("FrequencyBotFirestore 初始化成功")
        
        current_hour = int(time.time()) // 3600
        logger.info(f"\n當前小時 (UTC hour): {current_hour}")
        logger.info(f"當前時間: {datetime.now()}")
        
        # 檢查最近幾個小時的訊息
        hours_to_check = [current_hour, current_hour - 1, current_hour - 2]
        
        for hour in hours_to_check:
            local_time = datetime.fromtimestamp(hour * 3600)
            logger.info(f"\n=== 小時 {hour} ({local_time.strftime('%Y-%m-%d %H:00')}) ===")
            
            # 檢查是否有訊息
            doc_ref = bot.db.collection('broadcasts').document(str(hour))
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                message_count = data.get('message_count', 0)
                logger.info(f"訊息數量: {message_count}")
                
                # 檢查是否已生成廣播
                broadcast_doc = bot.db.collection('generated_broadcasts').document(str(hour)).get()
                if broadcast_doc.exists:
                    logger.info("廣播狀態: ✅ 已生成")
                else:
                    logger.info("廣播狀態: ❌ 未生成")
                    if message_count > 0:
                        logger.info(">>> 這個小時有訊息但未生成廣播！")
                        
                # 顯示前幾則訊息
                if message_count > 0:
                    messages = doc_ref.collection('messages').limit(3).stream()
                    logger.info("前幾則訊息:")
                    for msg in messages:
                        msg_data = msg.to_dict()
                        logger.info(f"  - {msg_data.get('content', '(無內容)')}")
            else:
                logger.info("沒有任何訊息記錄")
                
    except Exception as e:
        logger.error(f"檢查失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_pending_messages()