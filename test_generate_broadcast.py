#!/usr/bin/env python3
"""
測試廣播生成功能
"""

import os
import sys
from dotenv import load_dotenv
from frequency_bot_firestore import FrequencyBotFirestore
from knowledge_graph import KnowledgeGraph
import logging
import time

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def test_broadcast_generation():
    """測試廣播生成"""
    try:
        # 初始化知識圖譜
        try:
            knowledge_graph = KnowledgeGraph()
            logger.info("知識圖譜連接成功")
        except Exception as e:
            logger.warning(f"知識圖譜連接失敗: {e}")
            knowledge_graph = None
            
        # 初始化 FrequencyBotFirestore
        bot = FrequencyBotFirestore(knowledge_graph)
        logger.info("FrequencyBotFirestore 初始化成功")
        
        # 手動觸發過去時段的廣播生成
        hours_to_generate = [486120, 486121, 486122, 486123]
        
        for hour in hours_to_generate:
            logger.info(f"\n嘗試生成小時 {hour} 的廣播...")
            
            # 臨時修改 current_hour 以生成過去的廣播
            original_time = time.time
            time.time = lambda: hour * 3600
            
            try:
                result = bot.generate_hourly_broadcast()
                if result:
                    logger.info(f"廣播生成成功: {result}")
                else:
                    logger.info(f"廣播生成失敗或沒有訊息")
            finally:
                # 恢復原本的 time.time
                time.time = original_time
                
        # 檢查生成的廣播
        logger.info("\n檢查所有生成的廣播:")
        generated = bot.db.collection('generated_broadcasts').limit(10).stream()
        count = 0
        for gen_doc in generated:
            count += 1
            data = gen_doc.to_dict()
            logger.info(f"\n廣播 {gen_doc.id}:")
            logger.info(f"  訊息數: {data.get('message_count')}")
            logger.info(f"  內容: {data.get('content', '(無內容)')[:100]}...")
            logger.info(f"  優化類型: {data.get('optimization_type')}")
            
        logger.info(f"\n總共有 {count} 個廣播")
        
        # 測試取得最新廣播
        latest = bot.get_latest_broadcast()
        if latest:
            logger.info(f"\n最新廣播: {latest.get('content', '(無內容)')[:100]}...")
        else:
            logger.info("\n沒有最新廣播")
            
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_broadcast_generation()