#!/usr/bin/env python3
"""
簡單測試廣播生成
"""

import os
from dotenv import load_dotenv
from frequency_bot_firestore import FrequencyBotFirestore
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def test_simple_broadcast():
    """簡單測試廣播生成"""
    try:
        # 初始化 FrequencyBotFirestore（不使用知識圖譜）
        bot = FrequencyBotFirestore(knowledge_graph=None)
        logger.info("FrequencyBotFirestore 初始化成功")
        
        # 直接生成當前小時的廣播
        logger.info("開始生成廣播...")
        result = bot.generate_hourly_broadcast()
        
        if result:
            logger.info(f"廣播生成成功！")
            logger.info(f"訊息數: {result.get('message_count')}")
            logger.info(f"優化類型: {result.get('optimization_type')}")
            logger.info(f"內容預覽: {result.get('content', '(無內容)')[:200]}...")
        else:
            logger.info("沒有訊息可生成廣播")
            
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_broadcast()