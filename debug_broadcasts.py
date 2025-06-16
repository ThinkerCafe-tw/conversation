#!/usr/bin/env python3
"""
Debug broadcast timestamps to find the stuck 21:00 issue
"""

import os
import sys
from dotenv import load_dotenv
from frequency_bot_firestore import FrequencyBotFirestore
from knowledge_graph import KnowledgeGraph
import logging
import time
from datetime import datetime, timezone
import pytz

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def debug_broadcasts():
    """Debug broadcast timestamps"""
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
        
        # 顯示當前時間資訊
        current_time = time.time()
        current_hour = int(current_time) // 3600
        
        logger.info(f"\n=== 時間資訊 ===")
        logger.info(f"Current timestamp: {current_time}")
        logger.info(f"Current hour (UTC): {current_hour}")
        logger.info(f"Current local time: {datetime.now()}")
        logger.info(f"Current UTC time: {datetime.utcnow()}")
        
        # Convert UTC hour to local hour
        utc_dt = datetime.utcfromtimestamp(current_hour * 3600)
        local_dt = datetime.fromtimestamp(current_hour * 3600)
        logger.info(f"Current hour as UTC datetime: {utc_dt}")
        logger.info(f"Current hour as local datetime: {local_dt}")
        
        # 檢查所有生成的廣播
        logger.info(f"\n=== 所有生成的廣播 ===")
        generated = bot.db.collection('generated_broadcasts').order_by('timestamp', direction='DESCENDING').limit(10).stream()
        
        broadcasts_list = []
        for gen_doc in generated:
            data = gen_doc.to_dict()
            hour = int(gen_doc.id)
            timestamp = data.get('timestamp', 0)
            
            # Convert to local time for display
            utc_time = datetime.utcfromtimestamp(timestamp)
            local_time = datetime.fromtimestamp(timestamp)
            
            broadcasts_list.append({
                'hour': hour,
                'timestamp': timestamp,
                'utc_time': utc_time,
                'local_time': local_time,
                'message_count': data.get('message_count', 0),
                'content_preview': data.get('content', '')[:50] + '...'
            })
            
            logger.info(f"\nDocument ID (hour): {hour}")
            logger.info(f"  Timestamp: {timestamp}")
            logger.info(f"  UTC time: {utc_time}")
            logger.info(f"  Local time: {local_time}")
            logger.info(f"  Message count: {data.get('message_count')}")
            logger.info(f"  Content: {data.get('content', '')[:100]}...")
            logger.info(f"  Generated at: {data.get('generated_at')}")
            
        # 測試 get_latest_broadcast
        logger.info(f"\n=== 測試 get_latest_broadcast ===")
        latest = bot.get_latest_broadcast()
        if latest:
            latest_timestamp = latest.get('timestamp', 0)
            latest_local_time = datetime.fromtimestamp(latest_timestamp)
            logger.info(f"Latest broadcast timestamp: {latest_timestamp}")
            logger.info(f"Latest broadcast local time: {latest_local_time}")
            logger.info(f"Latest broadcast content: {latest.get('content', '')[:100]}...")
        else:
            logger.info("沒有找到最新廣播")
            
        # 檢查 24 小時前的時間戳
        twenty_four_hours_ago = int(time.time()) - (24 * 3600)
        logger.info(f"\n=== 24小時前時間戳 ===")
        logger.info(f"24 hours ago timestamp: {twenty_four_hours_ago}")
        logger.info(f"24 hours ago local time: {datetime.fromtimestamp(twenty_four_hours_ago)}")
        
        # 檢查哪些廣播在 24 小時內
        logger.info(f"\n=== 24小時內的廣播 ===")
        for b in broadcasts_list:
            if b['timestamp'] >= twenty_four_hours_ago:
                logger.info(f"Hour {b['hour']}: {b['local_time']} - {b['content_preview']}")
                
    except Exception as e:
        logger.error(f"Debug失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_broadcasts()